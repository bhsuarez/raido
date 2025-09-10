#!/usr/bin/env python3
"""
Enhanced artwork backfill script that uses both iTunes and MusicBrainz
with improved performance and parallel processing.
"""

import asyncio
import asyncpg
import httpx
import musicbrainzngs
import structlog
import time
from typing import Optional, Tuple, List
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append("/app")

from app.core.config import settings

logger = structlog.get_logger()

# Configure MusicBrainz
musicbrainzngs.set_useragent("Raido", "1.0", "https://raido.local")

class EnhancedArtworkService:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        self.session_timeout = httpx.Timeout(10.0)
        
    async def lookup_artwork_sources(self, artist: str, title: str, album: Optional[str] = None) -> Optional[str]:
        """Try multiple sources with proper rate limiting"""
        
        # Try iTunes first (faster, more reliable)
        artwork_url = await self._lookup_itunes(artist, title, album)
        if artwork_url:
            return artwork_url
            
        # Try MusicBrainz + Cover Art Archive
        artwork_url = await self._lookup_musicbrainz(artist, title, album)
        if artwork_url:
            return artwork_url
            
        return None
    
    async def _lookup_itunes(self, artist: str, title: str, album: Optional[str] = None) -> Optional[str]:
        """iTunes API lookup with better matching"""
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.session_timeout) as client:
                    # Try album search first if available
                    if album:
                        params = {
                            "term": f"{artist} {album}",
                            "entity": "album",
                            "limit": 5
                        }
                        response = await client.get("https://itunes.apple.com/search", params=params)
                        if response.status_code == 200:
                            data = response.json()
                            for result in data.get("results", []):
                                result_artist = result.get("artistName", "").lower()
                                if artist.lower() in result_artist or result_artist in artist.lower():
                                    artwork_url = result.get("artworkUrl100")
                                    if artwork_url:
                                        return artwork_url.replace("100x100bb", "600x600bb")
                    
                    # Fallback to song search
                    params = {
                        "term": f"{artist} {title}",
                        "entity": "song", 
                        "limit": 5
                    }
                    response = await client.get("https://itunes.apple.com/search", params=params)
                    if response.status_code == 200:
                        data = response.json()
                        for result in data.get("results", []):
                            result_artist = result.get("artistName", "").lower()
                            if artist.lower() in result_artist or result_artist in result_artist.lower():
                                artwork_url = result.get("artworkUrl100")
                                if artwork_url:
                                    return artwork_url.replace("100x100bb", "600x600bb")
                                    
            except Exception as e:
                logger.debug("iTunes lookup failed", error=str(e))
                
            # Add small delay to respect rate limits
            await asyncio.sleep(0.2)
            return None

    async def _lookup_musicbrainz(self, artist: str, title: str, album: Optional[str] = None) -> Optional[str]:
        """MusicBrainz + Cover Art Archive lookup"""
        async with self.semaphore:
            try:
                # Try album-based search first
                if album:
                    releases = musicbrainzngs.search_releases(artist=artist, release=album, limit=3)
                    for rel in releases.get("release-list", []) or []:
                        mbid = rel.get("id")
                        if mbid:
                            artwork_url = await self._check_cover_art_archive(mbid)
                            if artwork_url:
                                return artwork_url

                # Fallback to recording search
                recordings = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=3)
                for rec in recordings.get("recording-list", []) or []:
                    for rel in rec.get("release-list", []) or []:
                        mbid = rel.get("id")
                        if mbid:
                            artwork_url = await self._check_cover_art_archive(mbid)
                            if artwork_url:
                                return artwork_url

            except Exception as e:
                logger.debug("MusicBrainz lookup failed", error=str(e))
                
            # Rate limit for MusicBrainz (be nice)
            await asyncio.sleep(1.0)
            return None

    async def _check_cover_art_archive(self, mbid: str) -> Optional[str]:
        """Check Cover Art Archive for a specific MBID"""
        try:
            async with httpx.AsyncClient(timeout=self.session_timeout) as client:
                # Try different sizes
                for size in ["front-500", "front"]:
                    url = f"https://coverartarchive.org/release/{mbid}/{size}"
                    response = await client.head(url)  # Use HEAD to just check availability
                    if response.status_code == 200:
                        return url
        except Exception:
            pass
        return None

async def run_enhanced_backfill():
    """Run enhanced artwork backfill"""
    
    # Parse database URL
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    service = EnhancedArtworkService()
    updated_count = 0
    failed_count = 0
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        
        # Get tracks without artwork
        rows = await conn.fetch("""
            SELECT id, title, artist, album 
            FROM tracks 
            WHERE artwork_url IS NULL OR artwork_url = ''
            ORDER BY RANDOM()
            LIMIT 200
        """)
        
        total_tracks = len(rows)
        logger.info(f"Processing {total_tracks} tracks without artwork")
        
        # Process in batches to avoid overwhelming the APIs
        batch_size = 10
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            
            # Process batch concurrently
            tasks = []
            for row in batch:
                tasks.append(service.lookup_artwork_sources(row['artist'], row['title'], row['album']))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update database with results
            for j, result in enumerate(results):
                row = batch[j]
                if isinstance(result, str) and result:
                    # Update the track with the found artwork
                    await conn.execute("""
                        UPDATE tracks 
                        SET artwork_url = $1 
                        WHERE id = $2
                    """, result, row['id'])
                    updated_count += 1
                    logger.info("Updated artwork", 
                               track_id=row['id'], 
                               artist=row['artist'], 
                               title=row['title'],
                               artwork_url=result[:50] + "...")
                else:
                    failed_count += 1
                    logger.debug("No artwork found", 
                                track_id=row['id'], 
                                artist=row['artist'], 
                                title=row['title'])
            
            # Progress update
            processed = min(i + batch_size, total_tracks)
            logger.info(f"Progress: {processed}/{total_tracks} ({processed/total_tracks*100:.1f}%) - Found: {updated_count}, Failed: {failed_count}")
            
            # Brief pause between batches
            await asyncio.sleep(1.0)
    
    except Exception as e:
        logger.error("Backfill failed", error=str(e))
    
    finally:
        if 'conn' in locals():
            await conn.close()
        
        logger.info(f"Enhanced backfill completed - Updated: {updated_count}, Failed: {failed_count}")

if __name__ == "__main__":
    asyncio.run(run_enhanced_backfill())