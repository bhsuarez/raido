import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import configure_logging
from app.api.v1 import api_router
from app.core.websocket_manager import WebSocketManager

# Configure structured logging
configure_logging()
logger = structlog.get_logger()

# WebSocket manager instance
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("🏴‍☠️ Raido API starting up...")

    # Try to create database tables but don't crash if DB is unavailable in dev
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning("Database not available on startup; continuing", error=str(e))

    yield

    logger.info("🏴‍☠️ Raido API shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Raido API",
    description="AI Pirate Radio Backend API",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.APP_ENV == "development" else ["raido.local", "localhost"]
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Inject websocket manager into liquidsoap endpoints
from app.api.v1.endpoints import liquidsoap
liquidsoap.websocket_manager = websocket_manager

# Mount static files for TTS audio and artwork
app.mount("/static/tts", StaticFiles(directory="/shared/tts"), name="tts_files")

# Create artwork directory if it doesn't exist and mount it
artwork_dir = "/shared/artwork"
import os
os.makedirs(artwork_dir, exist_ok=True)
app.mount("/static/artwork", StaticFiles(directory=artwork_dir), name="artwork_files")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "raido-api"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.debug("Received WebSocket message", data=data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.debug("WebSocket client disconnected")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", exc_info=exc, path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
