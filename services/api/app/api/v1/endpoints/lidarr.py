"""Lidarr API proxy — routes frontend requests to the local Lidarr instance.

All calls are proxied with the configured API key injected server-side,
so the API key is never exposed to the browser.

Endpoints:
  GET  /lidarr/health              - check if Lidarr is reachable
  GET  /lidarr/status              - Lidarr system status
  GET  /lidarr/artist              - list all artists
  GET  /lidarr/artist/search       - search for an artist
  GET  /lidarr/artist/{id}         - get artist by Lidarr ID
  POST /lidarr/artist              - add artist to Lidarr
  GET  /lidarr/album               - list all albums
  GET  /lidarr/album/{id}          - get album by Lidarr ID
  GET  /lidarr/album/lookup        - search for album
  POST /lidarr/album/{id}/search   - trigger download search for album
  GET  /lidarr/queue               - current download queue
  DELETE /lidarr/queue/{id}        - remove from queue
  GET  /lidarr/history             - download history
  GET  /lidarr/rootfolder          - configured root folders
  GET  /lidarr/qualityprofile      - quality profiles
  GET  /lidarr/metadataprofile     - metadata profiles
  GET  /lidarr/wanted/missing      - missing albums
  GET  /lidarr/wanted/cutoff       - below-cutoff albums
"""

import os
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger()


def _lidarr_base() -> str:
    url = getattr(settings, "LIDARR_URL", None) or os.environ.get("LIDARR_URL", "http://lidarr:8686")
    return url.rstrip("/")


def _lidarr_api_key() -> str:
    key = getattr(settings, "LIDARR_API_KEY", None) or os.environ.get("LIDARR_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="LIDARR_API_KEY not configured in .env")
    return key


async def _proxy(
    method: str,
    path: str,
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    timeout: float = 15.0,
) -> dict:
    """Make an authenticated request to the Lidarr API."""
    url = f"{_lidarr_base()}/api/v1/{path.lstrip('/')}"
    headers = {"X-Api-Key": _lidarr_api_key(), "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                params=params,
                json=body,
                headers=headers,
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Lidarr error: {response.text[:300]}",
                )
            return response.json()
    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Lidarr — is it running?")
    except Exception as e:
        logger.error("Lidarr proxy error", path=path, error=str(e))
        raise HTTPException(status_code=502, detail=f"Lidarr proxy error: {e}")


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

@router.get("/health")
async def lidarr_health():
    """Check if Lidarr is reachable."""
    try:
        data = await _proxy("GET", "system/status")
        return {"ok": True, "version": data.get("version"), "appName": data.get("appName")}
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"ok": False, "detail": e.detail})


@router.get("/status")
async def lidarr_status():
    return await _proxy("GET", "system/status")


# ---------------------------------------------------------------------------
# Artists
# ---------------------------------------------------------------------------

@router.get("/artist")
async def list_artists():
    return await _proxy("GET", "artist")


@router.get("/artist/search")
async def search_artist(term: str = Query(..., description="Artist name to search")):
    return await _proxy("GET", "artist/lookup", params={"term": term})


@router.get("/artist/{artist_id}")
async def get_artist(artist_id: int):
    return await _proxy("GET", f"artist/{artist_id}")


@router.post("/artist")
async def add_artist(request: Request):
    body = await request.json()
    return await _proxy("POST", "artist", body=body)


@router.put("/artist/{artist_id}")
async def update_artist(artist_id: int, request: Request):
    body = await request.json()
    return await _proxy("PUT", f"artist/{artist_id}", body=body)


@router.delete("/artist/{artist_id}")
async def delete_artist(artist_id: int):
    return await _proxy("DELETE", f"artist/{artist_id}")


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------

@router.get("/album")
async def list_albums(artistId: Optional[int] = Query(None)):
    params = {}
    if artistId is not None:
        params["artistId"] = artistId
    return await _proxy("GET", "album", params=params or None)


@router.get("/album/lookup")
async def lookup_album(term: str = Query(...)):
    return await _proxy("GET", "album/lookup", params={"term": term})


@router.get("/album/{album_id}")
async def get_album(album_id: int):
    return await _proxy("GET", f"album/{album_id}")


@router.post("/album/{album_id}/search")
async def search_album(album_id: int):
    """Trigger Lidarr to search for downloads for this album."""
    return await _proxy("POST", "command", body={"name": "AlbumSearch", "albumIds": [album_id]})


# ---------------------------------------------------------------------------
# Download Queue
# ---------------------------------------------------------------------------

@router.get("/queue")
async def get_queue(page: int = Query(1), pageSize: int = Query(20)):
    return await _proxy("GET", "queue", params={"page": page, "pageSize": pageSize})


@router.delete("/queue/{queue_id}")
async def delete_queue_item(queue_id: int, blacklist: bool = Query(False)):
    return await _proxy("DELETE", f"queue/{queue_id}", params={"blacklist": str(blacklist).lower()})


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@router.get("/history")
async def get_history(page: int = Query(1), pageSize: int = Query(20)):
    return await _proxy("GET", "history", params={"page": page, "pageSize": pageSize, "sortKey": "date", "sortDirection": "descending"})


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

@router.get("/rootfolder")
async def get_root_folders():
    return await _proxy("GET", "rootfolder")


@router.get("/qualityprofile")
async def get_quality_profiles():
    return await _proxy("GET", "qualityprofile")


@router.get("/metadataprofile")
async def get_metadata_profiles():
    return await _proxy("GET", "metadataprofile")


# ---------------------------------------------------------------------------
# Wanted
# ---------------------------------------------------------------------------

@router.get("/wanted/missing")
async def get_missing(page: int = Query(1), pageSize: int = Query(20)):
    return await _proxy("GET", "wanted/missing", params={"page": page, "pageSize": pageSize})


@router.get("/wanted/cutoff")
async def get_cutoff(page: int = Query(1), pageSize: int = Query(20)):
    return await _proxy("GET", "wanted/cutoff", params={"page": page, "pageSize": pageSize})
