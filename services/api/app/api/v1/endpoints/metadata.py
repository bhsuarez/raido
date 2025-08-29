"""
Metadata extraction and management API endpoints.
Provides endpoints for scanning audio files and extracting comprehensive metadata.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog
from pathlib import Path
import os

from app.core.database import get_db
from app.models import Track
from app.services.metadata_extractor import MetadataExtractor

router = APIRouter()
logger = structlog.get_logger()


class MetadataExtractRequest(BaseModel):
    """Request model for metadata extraction"""
    file_path: Optional[str] = None
    directory_path: Optional[str] = None
    recursive: bool = True
    update_existing: bool = True


class MetadataResponse(BaseModel):
    """Response model for metadata extraction"""
    status: str
    files_processed: int
    files_updated: int
    files_created: int
    errors: List[str]


@router.post("/extract", response_model=MetadataResponse)
async def extract_metadata(
    request: MetadataExtractRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Extract metadata from audio files and update the database.
    Can process a single file or an entire directory.
    """
    try:
        logger.info("Metadata extraction requested", request=request.dict())
        
        if not request.file_path and not request.directory_path:
            raise HTTPException(status_code=400, detail="Either file_path or directory_path must be provided")
        
        if request.file_path and request.directory_path:
            raise HTTPException(status_code=400, detail="Provide either file_path or directory_path, not both")
        
        # Start extraction in background
        if request.file_path:
            background_tasks.add_task(
                _extract_single_file,
                request.file_path,
                request.update_existing,
                db
            )
            return MetadataResponse(
                status="started",
                files_processed=0,
                files_updated=0, 
                files_created=0,
                errors=[]
            )
        else:
            background_tasks.add_task(
                _extract_directory,
                request.directory_path,
                request.recursive,
                request.update_existing,
                db
            )
            return MetadataResponse(
                status="started",
                files_processed=0,
                files_updated=0,
                files_created=0,
                errors=[]
            )
            
    except Exception as e:
        logger.error("Failed to start metadata extraction", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start extraction: {str(e)}")


@router.get("/scan_music_directory")
async def scan_music_directory(
    background_tasks: BackgroundTasks,
    update_existing: bool = True
):
    """
    Scan the default music directory (/mnt/music) for audio files and extract metadata.
    This is a convenience endpoint for scanning the main music library.
    """
    try:
        music_dir = "/mnt/music"
        if not os.path.exists(music_dir):
            raise HTTPException(status_code=404, detail="Music directory not found")
        
        # Start background scanning
        background_tasks.add_task(_scan_music_library, music_dir, update_existing)
        
        return {
            "status": "started",
            "message": f"Started scanning music directory: {music_dir}",
            "directory": music_dir
        }
        
    except Exception as e:
        logger.error("Failed to start music directory scan", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


@router.get("/file/{file_id}/metadata")
async def get_file_metadata(file_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed metadata for a specific track"""
    try:
        result = await db.execute(select(Track).where(Track.id == file_id))
        track = result.scalar_one_or_none()
        
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        return {
            "track_id": track.id,
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "year": track.year,
            "genre": track.genre,
            "duration_sec": track.duration_sec,
            "file_path": track.file_path,
            "artwork_url": track.artwork_url,
            "play_count": track.play_count,
            "last_played_at": track.last_played_at.isoformat() if track.last_played_at else None,
            "created_at": track.created_at.isoformat() if track.created_at else None,
            "tags": track.tags
        }
        
    except Exception as e:
        logger.error("Failed to get track metadata", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get metadata: {str(e)}")


@router.post("/refresh/{file_id}")
async def refresh_file_metadata(
    file_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Re-extract metadata for a specific track from its audio file"""
    try:
        result = await db.execute(select(Track).where(Track.id == file_id))
        track = result.scalar_one_or_none()
        
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        if not track.file_path or not os.path.exists(track.file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Start metadata refresh in background
        background_tasks.add_task(_refresh_track_metadata, track.id, track.file_path, db)
        
        return {
            "status": "started",
            "message": f"Started metadata refresh for track: {track.title}",
            "track_id": track.id
        }
        
    except Exception as e:
        logger.error("Failed to start metadata refresh", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start refresh: {str(e)}")


async def _extract_single_file(file_path: str, update_existing: bool, db: AsyncSession):
    """Background task to extract metadata from a single file"""
    try:
        logger.info("Starting single file metadata extraction", file_path=file_path)
        
        metadata = await MetadataExtractor.extract_file_metadata(file_path)
        if not metadata:
            logger.warning("No metadata extracted", file_path=file_path)
            return
        
        await _update_or_create_track(metadata, update_existing, db)
        await db.commit()
        
        logger.info("Completed single file extraction", file_path=file_path)
        
    except Exception as e:
        logger.error("Failed single file extraction", file_path=file_path, error=str(e))
        await db.rollback()


async def _extract_directory(directory_path: str, recursive: bool, update_existing: bool, db: AsyncSession):
    """Background task to extract metadata from a directory"""
    try:
        logger.info("Starting directory metadata extraction", 
                   directory=directory_path, recursive=recursive)
        
        metadata_list = await MetadataExtractor.scan_directory(directory_path, recursive)
        
        files_processed = 0
        files_updated = 0
        files_created = 0
        
        for metadata in metadata_list:
            try:
                result = await _update_or_create_track(metadata, update_existing, db)
                files_processed += 1
                if result == "updated":
                    files_updated += 1
                elif result == "created":
                    files_created += 1
                    
                # Commit in batches to avoid memory issues
                if files_processed % 50 == 0:
                    await db.commit()
                    logger.info("Batch commit", processed=files_processed)
                    
            except Exception as e:
                logger.error("Failed to process file metadata", 
                           file_path=metadata.get('file_path'), error=str(e))
                continue
        
        await db.commit()
        
        logger.info("Completed directory extraction", 
                   directory=directory_path, 
                   processed=files_processed,
                   updated=files_updated,
                   created=files_created)
        
    except Exception as e:
        logger.error("Failed directory extraction", 
                    directory=directory_path, error=str(e))
        await db.rollback()


async def _scan_music_library(music_dir: str, update_existing: bool):
    """Background task to scan the main music library"""
    try:
        from app.core.database import get_db_session
        
        async with get_db_session() as db:
            await _extract_directory(music_dir, True, update_existing, db)
            
    except Exception as e:
        logger.error("Failed music library scan", directory=music_dir, error=str(e))


async def _refresh_track_metadata(track_id: int, file_path: str, db: AsyncSession):
    """Background task to refresh metadata for a specific track"""
    try:
        logger.info("Starting metadata refresh", track_id=track_id, file_path=file_path)
        
        metadata = await MetadataExtractor.extract_file_metadata(file_path)
        if not metadata:
            logger.warning("No metadata extracted during refresh", file_path=file_path)
            return
        
        # Update the specific track
        result = await db.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()
        
        if track:
            _update_track_from_metadata(track, metadata)
            await db.commit()
            logger.info("Completed metadata refresh", track_id=track_id)
        else:
            logger.warning("Track not found during refresh", track_id=track_id)
        
    except Exception as e:
        logger.error("Failed metadata refresh", track_id=track_id, error=str(e))
        await db.rollback()


async def _update_or_create_track(metadata: Dict[str, Any], update_existing: bool, db: AsyncSession) -> str:
    """Update existing track or create new one from metadata"""
    
    file_path = metadata.get('file_path')
    if not file_path:
        return "skipped"
    
    # Look for existing track by file path
    result = await db.execute(
        select(Track).where(Track.file_path == file_path)
    )
    track = result.scalar_one_or_none()
    
    if track:
        if update_existing:
            _update_track_from_metadata(track, metadata)
            return "updated"
        else:
            return "skipped"
    else:
        # Create new track
        track = Track(
            title=metadata.get('title', 'Unknown Title'),
            artist=metadata.get('artist', 'Unknown Artist'),
            album=metadata.get('album'),
            year=metadata.get('year'),
            genre=metadata.get('genre'),
            file_path=file_path,
            duration_sec=metadata.get('duration_sec'),
            tags=metadata
        )
        db.add(track)
        return "created"


def _update_track_from_metadata(track: Track, metadata: Dict[str, Any]):
    """Update a track object with extracted metadata"""
    
    # Update basic fields
    if metadata.get('title'):
        track.title = metadata['title']
    if metadata.get('artist'):
        track.artist = metadata['artist']
    if metadata.get('album'):
        track.album = metadata['album']
    if metadata.get('year'):
        track.year = metadata['year']
    if metadata.get('genre'):
        track.genre = metadata['genre']
    if metadata.get('duration_sec'):
        track.duration_sec = metadata['duration_sec']
    
    # Store all metadata in tags field
    track.tags = metadata