from fastapi import APIRouter

from app.api.v1.endpoints import now_playing, stream, admin, liquidsoap, metadata, request_queue

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(now_playing.router, prefix="/now", tags=["now-playing"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(liquidsoap.router, prefix="/liquidsoap", tags=["liquidsoap"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
api_router.include_router(request_queue.router, prefix="/queue", tags=["queue"])