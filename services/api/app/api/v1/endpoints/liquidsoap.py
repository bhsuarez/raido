from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog
import httpx
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import Track, Play, Station
from app.core.websocket_manager import WebSocketManager
from app.services.metadata_extractor import MetadataExtractor

router = APIRouter()
logger = structlog.get_logger()

# This would be injected in main.py
websocket_manager: Optional[WebSocketManager] = None

class TrackChangeRequest(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    filename: Optional[str] = None
    duration: Optional[float] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    station: Optional[str] = "main"  # Station identifier (main, christmas, etc.)
    metadata: Dict[str, Any] = {}

@router.post("/track_change")
async def track_change_notification(
    request: TrackChangeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handle track change notifications from Liquidsoap"""
    try:
        logger.info("Received track change notification",
                   station=request.station,
                   track_data=request.dict())
        
        # Find or create track record
        track = None
        if request.filename:
            # Try to find existing track by filename
            result = await db.execute(
                select(Track).where(Track.file_path.endswith(request.filename))
            )
            tracks = result.scalars().all()
            track = tracks[0] if tracks else None
        
        if not track and (request.title and request.artist):
            # Try to find by title/artist
            result = await db.execute(
                select(Track).where(
                    Track.title == request.title,
                    Track.artist == request.artist
                )
            )
            tracks = result.scalars().all()
            track = tracks[0] if tracks else None
        
        # Create track if not found
        if not track:
            # Generate unique file_path if not provided
            file_path = request.filename
            if not file_path:
                # Use artist-title as fallback to avoid empty string conflicts
                safe_artist = (request.artist or "Unknown").replace(" ", "_").replace("/", "_")
                safe_title = (request.title or "Unknown").replace(" ", "_").replace("/", "_")
                file_path = f"liquidsoap://{safe_artist}-{safe_title}"
            
            # Use filename parsing as fallback for missing metadata
            filename_metadata = {}
            if file_path and not file_path.startswith("liquidsoap://"):
                # Try to extract metadata from filename/path
                filename_metadata = MetadataExtractor._parse_filename_metadata(file_path)
                logger.debug("Parsed filename metadata", file_path=file_path, metadata=filename_metadata)
            
            # Use parsed metadata as fallback
            title = request.title or filename_metadata.get('title') or "Unknown Title"
            artist = request.artist or filename_metadata.get('artist') or "Unknown Artist" 
            album = request.album or filename_metadata.get('album')
            genre = request.genre or filename_metadata.get('genre')
            
            # Try to get artwork URL
            artwork_url = await _lookup_artwork(artist, title, album)
            
            # Parse year as integer if provided
            year_int = None
            year_value = request.year or filename_metadata.get('year')
            if year_value and str(year_value).strip() and str(year_value).strip().isdigit():
                year_int = int(str(year_value).strip())
            
            track = Track(
                title=title,
                artist=artist,
                album=album,
                year=year_int,
                genre=genre,
                file_path=file_path,
                duration_sec=request.duration,
                artwork_url=artwork_url,
                tags=request.metadata
            )
            db.add(track)
            await db.flush()  # Get the ID
        else:
            # Update existing track with any new metadata we received
            updated = False
            if request.duration and not track.duration_sec:
                track.duration_sec = request.duration
                updated = True
            if request.year and not track.year:
                year_int = None
                if request.year.strip() and request.year.strip().isdigit():
                    year_int = int(request.year.strip())
                    track.year = year_int
                    updated = True
            if request.genre and not track.genre:
                track.genre = request.genre
                updated = True
            if not track.artwork_url:
                artwork_url = await _lookup_artwork(request.artist, request.title, request.album)
                if artwork_url:
                    track.artwork_url = artwork_url
                    updated = True

        # Ensure the track is associated with the station that reported it
        station_identifier = (request.station or "main").lower()
        station_obj = None
        try:
            station_result = await db.execute(
                select(Station).where(func.lower(Station.identifier) == station_identifier)
            )
            station_obj = station_result.scalar_one_or_none()

            if not station_obj:
                # Create a lightweight station record if it doesn't exist yet
                station_obj = Station(
                    identifier=station_identifier,
                    name=station_identifier.capitalize(),
                    genre=request.genre,
                )
                db.add(station_obj)
                await db.flush()

            await db.refresh(track)
            if station_obj not in track.stations:
                track.stations.append(station_obj)

            # Maintain station tags on the track for quick filtering
            if track.tags is None:
                track.tags = {"stations": [station_identifier]}
            elif isinstance(track.tags, dict):
                stations = track.tags.get("stations")
                if isinstance(stations, list):
                    if station_identifier not in stations:
                        stations.append(station_identifier)
                        track.tags["stations"] = stations
                else:
                    track.tags["stations"] = [station_identifier]
            else:
                track.tags = {"stations": [station_identifier]}
        except Exception as assoc_err:
            logger.warning(
                "Failed to associate track with station",
                track_id=getattr(track, "id", None),
                station=station_identifier,
                error=str(assoc_err),
            )

        # End any current playing track
        current_play_result = await db.execute(
            select(Play)
            .where(Play.ended_at.is_(None))
            .where(func.lower(func.coalesce(Play.station_identifier, "main")) == station_identifier)
            .order_by(Play.started_at.desc())
            .limit(1)
        )
        current_play = current_play_result.scalar_one_or_none()
        
        if current_play:
            current_play.ended_at = datetime.now(timezone.utc)
            current_play.elapsed_ms = int((current_play.ended_at - current_play.started_at).total_seconds() * 1000)
        
        # Create new play record with station information
        new_play = Play(
            track_id=track.id,
            started_at=datetime.now(timezone.utc),
            liquidsoap_id=request.metadata.get("liquidsoap_id"),
            source_type="playlist",
            station_id=station_obj.id if station_obj else None,
            station_identifier=station_identifier
        )
        # Station ID is now properly set from station_obj lookup
        request.metadata["station"] = request.station
        db.add(new_play)
        
        # Update track statistics
        track.play_count += 1
        track.last_played_at = new_play.started_at
        
        # Capture artwork_url before commit (async SQLAlchemy expires objects after commit)
        artwork_url_response = track.artwork_url or ""

        await db.commit()
        
        # Broadcast to WebSocket clients
        if websocket_manager:
            await websocket_manager.broadcast_track_change({
                "track": {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "album": track.album,
                    "duration_sec": track.duration_sec,
                    "artwork_url": track.artwork_url
                },
                "play": {
                    "id": new_play.id,
                    "started_at": new_play.started_at.isoformat(),
                    "liquidsoap_id": new_play.liquidsoap_id
                },
                "station": request.station
            })
        
        # Commentary generation is handled by the DJ worker service
        # which monitors track changes and generates commentary based on settings
        
        # Return artwork_url so Liquidsoap can inject it as StreamUrl in the ICY metadata
        return {"status": "success", "track_id": track.id, "play_id": new_play.id, "artwork_url": artwork_url_response}
        
    except Exception as e:
        logger.error("Failed to handle track change", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process track change: {str(e)}")

@router.get("/status")
async def liquidsoap_status():
    """Get Liquidsoap status via telnet interface"""
    try:
        from app.services.liquidsoap_client import LiquidsoapClient
        
        client = LiquidsoapClient()
        status = client.get_all_status()
        
        return {
            "status": "running",
            "liquidsoap_metadata": status.get('metadata', {}),
            "queue_info": status.get('queue', {}),
            "uptime_seconds": status.get('uptime'),
            "available_commands": status.get('available_commands', []),
            "raw_status": status
        }
        
    except Exception as e:
        logger.error("Failed to get Liquidsoap status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get stream status")

@router.post("/skip")
async def skip_current_track(station: str = "main", db: AsyncSession = Depends(get_db)):
    """Skip the currently playing track"""
    try:
        logger.info("Track skip requested", station=station)

        # Mark current play as skipped in database
        current_play_result = await db.execute(
            select(Play).where(Play.ended_at.is_(None)).order_by(Play.started_at.desc()).limit(1)
        )
        current_play = current_play_result.scalar_one_or_none()

        if current_play:
            current_play.was_skipped = True
            await db.commit()

        # Determine Liquidsoap host and port based on station
        if station == "christmas":
            liquidsoap_host = "christmas-liquidsoap"
            liquidsoap_port = 1235
        elif station == "recent":
            liquidsoap_host = "recent-liquidsoap"
            liquidsoap_port = 1236
        else:
            liquidsoap_host = "liquidsoap"
            liquidsoap_port = 1234

        # Connect to Liquidsoap telnet and skip track
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)

        try:
            # Connect to Liquidsoap telnet interface
            sock.connect((liquidsoap_host, liquidsoap_port))
            
            # Send skip command; matches LiquidsoapClient implementation
            command = "music.skip\n"
            sock.send(command.encode())
            
            # Read response
            response = sock.recv(1024).decode().strip()
            logger.info("Liquidsoap skip response", command=command.strip(), response=response)
            
            return {"status": "success", "message": "Track skipped", "liquidsoap_response": response}
            
        finally:
            sock.close()
        
    except Exception as e:
        logger.error("Failed to skip track", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to skip track: {str(e)}")

@router.post("/inject_commentary")
async def inject_commentary_file(
    filename: str,
    station: str = "main",
    db: AsyncSession = Depends(get_db)
):
    """Inject a commentary file into the stream"""
    try:
        logger.info("Commentary injection requested", filename=filename, station=station)

        # Determine Liquidsoap host, port, and queue name based on station
        if station == "christmas":
            liquidsoap_host = "christmas-liquidsoap"
            liquidsoap_port = 1235
            queue_name = "tts_christmas"
        elif station == "recent":
            liquidsoap_host = "recent-liquidsoap"
            liquidsoap_port = 1236
            queue_name = "tts_recent"
        else:
            liquidsoap_host = "liquidsoap"
            liquidsoap_port = 1234
            queue_name = "tts"

        # Connect to Liquidsoap telnet and inject TTS audio
        import socket

        def ls_cmd(host, port, cmd, timeout=5.0):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                s.connect((host, port))
                s.send(f"{cmd}\n".encode())
                resp = s.recv(4096).decode(errors="ignore").strip()
                return resp
            finally:
                s.close()

        # Guard: only inject if the TTS queue is currently empty to avoid
        # back-to-back commentaries causing wrong track pairings.
        try:
            queued_resp = ls_cmd(liquidsoap_host, liquidsoap_port, f"{queue_name}.queue")
            # Response is space-separated RIDs or empty
            queued_rids = [r for r in queued_resp.split() if r.isdigit()]
            if queued_rids:
                logger.warning(
                    "TTS queue already occupied — skipping injection to prevent double commentary",
                    queue=queue_name,
                    queued_rids=queued_rids,
                )
                return {"status": "skipped", "message": "TTS queue already has a pending commentary", "queued_rids": queued_rids}
        except Exception as qcheck_err:
            logger.warning("Could not check TTS queue before injection; proceeding anyway", error=str(qcheck_err))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)

        try:
            # Connect to Liquidsoap telnet interface
            sock.connect((liquidsoap_host, liquidsoap_port))

            # Push the commentary file to TTS queue
            command = f"{queue_name}.push /shared/tts/{filename}\n"
            sock.send(command.encode())
            
            # Read response
            response = sock.recv(1024).decode().strip()
            logger.info("Liquidsoap response", command=command.strip(), response=response)
            
            return {"status": "success", "message": f"Commentary {filename} injected into stream", "liquidsoap_response": response}
            
        finally:
            sock.close()
        
    except Exception as e:
        logger.error("Failed to inject commentary", error=str(e), filename=filename)
        raise HTTPException(status_code=500, detail=f"Failed to inject commentary: {str(e)}")

async def _lookup_artwork(artist: Optional[str], title: Optional[str], album: Optional[str] = None) -> Optional[str]:
    """Lookup album artwork.

    Order:
    1) iTunes Search API (album preferred, then song)
    2) MusicBrainz + Cover Art Archive fallback
    """
    if not artist or not title:
        return None
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use album if available, otherwise search by artist + title
            if album:
                query = f"{artist} {album}"
                entity = "album"
            else:
                query = f"{artist} {title}"
                entity = "song"
            
            params = {
                "term": query,
                "entity": entity,
                "limit": 3
            }
            
            response = await client.get("https://itunes.apple.com/search", params=params)
            if response.status_code != 200:
                return None
            
            data = response.json()
            results = data.get("results", [])
            
            for result in results:
                # Check if it's a reasonable match
                result_artist = result.get("artistName", "").lower()
                if artist.lower() in result_artist or result_artist in artist.lower():
                    artwork_url = result.get("artworkUrl100")
                    if artwork_url:
                        # Get higher resolution version
                        artwork_url = artwork_url.replace("100x100", "600x600")
                        logger.debug("Found artwork via iTunes", artist=artist, title=title, url=artwork_url)
                        return artwork_url
            
            return None

    except Exception as e:
        logger.debug("Artwork lookup via iTunes failed", error=str(e))

    # Fallback to MusicBrainz + Cover Art Archive
    try:
        import musicbrainzngs
        musicbrainzngs.set_useragent("Raido", "1.0", "https://raido.local")

        # Prefer album-based search first if available
        if album:
            res = musicbrainzngs.search_releases(artist=artist, release=album, limit=3)
            for rel in res.get("release-list", []) or []:
                mbid = rel.get("id")
                if not mbid:
                    continue
                url = f"https://coverartarchive.org/release/{mbid}/front-500"
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                            logger.debug("Found artwork via CAA (album)", url=url)
                            return url
                except Exception:
                    pass

        # Recording-based fallback
        res = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=3)
        for rec in res.get("recording-list", []) or []:
            for rel in rec.get("release-list", []) or []:
                mbid = rel.get("id")
                if not mbid:
                    continue
                url = f"https://coverartarchive.org/release/{mbid}/front-500"
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                            logger.debug("Found artwork via CAA (recording)", url=url)
                            return url
                except Exception:
                    pass

    except Exception as e:
        logger.debug("MusicBrainz lookup failed", error=str(e))

    return None
