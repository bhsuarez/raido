from fastapi import APIRouter

from app.api.v1.endpoints import (
    now_playing,
    stream,
    admin,
    liquidsoap,
    metadata,
    request_queue,
    artwork,
    tracks,
    stations,
    auth,
    enrichment,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(now_playing.router, prefix="/now", tags=["now-playing"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(liquidsoap.router, prefix="/liquidsoap", tags=["liquidsoap"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
api_router.include_router(request_queue.router, prefix="/queue", tags=["queue"])
api_router.include_router(artwork.router, prefix="/artwork", tags=["artwork"])
api_router.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
api_router.include_router(stations.router, prefix="/stations", tags=["stations"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(enrichment.router, prefix="/enrichment", tags=["enrichment"])
