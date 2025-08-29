"""
Artwork extraction and serving endpoint.
Extracts album artwork directly from audio file ID3/metadata tags.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog
from pathlib import Path
import os
from typing import Optional
import io

from app.core.database import get_db
from app.models import Track
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4
from mutagen.flac import FLAC

router = APIRouter()
logger = structlog.get_logger()


@router.get("/track/{track_id}")
async def get_track_artwork(
    track_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Extract and serve artwork directly from audio file ID3 tags"""
    try:
        # Get track from database
        result = await db.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()
        
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        if not track.file_path or not os.path.exists(track.file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Extract artwork from audio file
        artwork_data, mime_type = await _extract_artwork_from_file(track.file_path)
        
        if not artwork_data:
            raise HTTPException(status_code=404, detail="No artwork found in audio file")
        
        # Serve the artwork
        return StreamingResponse(
            io.BytesIO(artwork_data),
            media_type=mime_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                "Content-Disposition": f'inline; filename="artwork_{track_id}.{_get_file_extension(mime_type)}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get track artwork", track_id=track_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to extract artwork: {str(e)}")


@router.post("/track/{track_id}/extract_and_cache")
async def extract_and_cache_artwork(
    track_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Extract artwork from audio file and cache it as a static file"""
    try:
        # Get track from database
        result = await db.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()
        
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        if not track.file_path or not os.path.exists(track.file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Check if artwork exists in file
        artwork_data, mime_type = await _extract_artwork_from_file(track.file_path)
        
        if artwork_data:
            # Save artwork to static files directory
            artwork_dir = Path("/shared/artwork")
            artwork_dir.mkdir(exist_ok=True)
            
            file_extension = _get_file_extension(mime_type)
            artwork_filename = f"track_{track_id}.{file_extension}"
            artwork_path = artwork_dir / artwork_filename
            
            # Write artwork data to file
            with open(artwork_path, "wb") as f:
                f.write(artwork_data)
            
            # Update the track's artwork_url to point to the cached file
            new_artwork_url = f"/static/artwork/{artwork_filename}"
            
            await db.execute(
                update(Track).where(Track.id == track_id).values(artwork_url=new_artwork_url)
            )
            await db.commit()
            
            logger.info("Extracted and cached track artwork", 
                       track_id=track_id, artwork_url=new_artwork_url, file_size=len(artwork_data))
            
            return {
                "status": "extracted_and_cached", 
                "artwork_url": new_artwork_url,
                "file_size": len(artwork_data),
                "mime_type": mime_type,
                "message": "Artwork extracted from audio file and cached"
            }
        else:
            return {
                "status": "no_artwork",
                "message": "No embedded artwork found in audio file"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to extract and cache artwork", track_id=track_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to extract artwork: {str(e)}")


@router.post("/batch_extract")
async def batch_extract_artwork(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Extract and cache artwork for tracks that have embedded artwork but no artwork_url"""
    try:
        # Find tracks without artwork_url but with has_artwork flag in tags
        result = await db.execute(
            select(Track).where(Track.artwork_url.is_(None)).limit(limit)
        )
        tracks = result.scalars().all()
        
        extracted_count = 0
        failed_count = 0
        
        for track in tracks:
            if not track.file_path or not os.path.exists(track.file_path):
                continue
                
            try:
                # Check if this track has embedded artwork
                artwork_data, mime_type = await _extract_artwork_from_file(track.file_path)
                
                if artwork_data:
                    # Save artwork to static files directory
                    artwork_dir = Path("/shared/artwork")
                    artwork_dir.mkdir(exist_ok=True)
                    
                    file_extension = _get_file_extension(mime_type)
                    artwork_filename = f"track_{track.id}.{file_extension}"
                    artwork_path = artwork_dir / artwork_filename
                    
                    # Write artwork data to file
                    with open(artwork_path, "wb") as f:
                        f.write(artwork_data)
                    
                    # Update the track's artwork_url
                    new_artwork_url = f"/static/artwork/{artwork_filename}"
                    track.artwork_url = new_artwork_url
                    extracted_count += 1
                    
                    if extracted_count % 10 == 0:
                        await db.commit()
                        logger.info("Batch progress", extracted=extracted_count, failed=failed_count)
                        
            except Exception as e:
                failed_count += 1
                logger.error("Failed to process track", track_id=track.id, error=str(e))
                continue
        
        await db.commit()
        
        return {
            "status": "completed",
            "tracks_processed": len(tracks),
            "artwork_extracted": extracted_count,
            "failed": failed_count,
            "message": f"Extracted artwork for {extracted_count} tracks"
        }
        
    except Exception as e:
        logger.error("Failed batch artwork extraction", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch extraction failed: {str(e)}")


async def _extract_artwork_from_file(file_path: str) -> tuple[Optional[bytes], Optional[str]]:
    """Extract artwork data and MIME type from audio file"""
    try:
        path = Path(file_path)
        file_format = path.suffix.lower()
        
        # Load the audio file
        audio_file = MutagenFile(file_path)
        if not audio_file:
            return None, None
        
        # Extract artwork based on file format
        if file_format == '.mp3':
            return _extract_mp3_artwork(audio_file)
        elif file_format in ['.m4a', '.mp4']:
            return _extract_mp4_artwork(audio_file)
        elif file_format == '.flac':
            return _extract_flac_artwork(audio_file)
        else:
            logger.debug("Unsupported format for artwork extraction", format=file_format)
            return None, None
            
    except Exception as e:
        logger.error("Error extracting artwork", file_path=file_path, error=str(e))
        return None, None


def _extract_mp3_artwork(audio_file) -> tuple[Optional[bytes], Optional[str]]:
    """Extract artwork from MP3 ID3 tags"""
    try:
        if not audio_file.tags:
            return None, None
        
        # Look for APIC frames (Attached Picture)
        for key in audio_file.tags:
            if key.startswith('APIC'):
                apic = audio_file.tags[key]
                if apic.data:
                    return apic.data, apic.mime
        
        return None, None
        
    except Exception as e:
        logger.debug("Failed to extract MP3 artwork", error=str(e))
        return None, None


def _extract_mp4_artwork(audio_file) -> tuple[Optional[bytes], Optional[str]]:
    """Extract artwork from MP4/M4A files"""
    try:
        if not audio_file.tags or 'covr' not in audio_file.tags:
            return None, None
        
        cover_data = audio_file.tags['covr'][0]
        
        # Determine MIME type based on format
        if hasattr(cover_data, 'imageformat'):
            if cover_data.imageformat == cover_data.FORMAT_JPEG:
                mime_type = "image/jpeg"
            elif cover_data.imageformat == cover_data.FORMAT_PNG:
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg"  # Default fallback
        else:
            # Try to detect from data
            if cover_data[:3] == b'\xff\xd8\xff':
                mime_type = "image/jpeg"
            elif cover_data[:8] == b'\x89PNG\r\n\x1a\n':
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg"  # Default fallback
        
        return bytes(cover_data), mime_type
        
    except Exception as e:
        logger.debug("Failed to extract MP4 artwork", error=str(e))
        return None, None


def _extract_flac_artwork(audio_file) -> tuple[Optional[bytes], Optional[str]]:
    """Extract artwork from FLAC files"""
    try:
        if not hasattr(audio_file, 'pictures') or not audio_file.pictures:
            return None, None
        
        # Get the first picture (usually front cover)
        picture = audio_file.pictures[0]
        return picture.data, picture.mime
        
    except Exception as e:
        logger.debug("Failed to extract FLAC artwork", error=str(e))
        return None, None


def _get_file_extension(mime_type: str) -> str:
    """Get file extension from MIME type"""
    mime_to_ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/bmp": "bmp",
        "image/webp": "webp"
    }
    return mime_to_ext.get(mime_type, "jpg")