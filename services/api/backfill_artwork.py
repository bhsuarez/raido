#!/usr/bin/env python3
"""
Backfill artwork for existing tracks in the database
"""
import asyncio
import httpx
import structlog
from urllib.parse import quote
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, update
import os
import sys

# Add the app directory to the path
sys.path.insert(0, "/app")
from app.models import Track

logger = structlog.get_logger()

async def lookup_artwork(artist: Optional[str], title: Optional[str], album: Optional[str] = None) -> Optional[str]:
    """Lookup artwork via iTunes, falling back to MusicBrainz + CAA."""
    if not artist or not title:
        return None
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try album search first if album is provided
            if album:
                query = f"{artist} {album}"
                entity = "album"
                params = {"term": query, "entity": entity, "limit": 3}
                response = await client.get("https://itunes.apple.com/search", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    for result in data.get("results", []):
                        artwork_url = result.get("artworkUrl100", "")
                        if artwork_url:
                            # Upgrade to higher resolution
                            artwork_url = artwork_url.replace("/100x100bb.", "/600x600bb.")
                            logger.info("Found album artwork (iTunes)", artist=artist, album=album, url=artwork_url)
                            return artwork_url
            
            # Fallback to song search
            query = f"{artist} {title}"
            entity = "song"
            params = {"term": query, "entity": entity, "limit": 5}
            response = await client.get("https://itunes.apple.com/search", params=params)
            
            if response.status_code == 200:
                data = response.json()
                for result in data.get("results", []):
                    artwork_url = result.get("artworkUrl100", "")
                    if artwork_url:
                        # Upgrade to higher resolution
                        artwork_url = artwork_url.replace("/100x100bb.", "/600x600bb.")
                        logger.info("Found song artwork (iTunes)", artist=artist, title=title, url=artwork_url)
                        return artwork_url
                        
    except Exception as e:
        logger.warn("iTunes API lookup failed", artist=artist, title=title, error=str(e))

    # Fallback: MusicBrainz + Cover Art Archive
    try:
        import musicbrainzngs
        musicbrainzngs.set_useragent("Raido", "1.0", "https://raido.local")

        async def try_caa(mbid: str) -> Optional[str]:
            url = f"https://coverartarchive.org/release/{mbid}/front-500"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                        logger.info("Found artwork (CAA)", url=url)
                        return url
            except Exception:
                return None
            return None

        if album:
            res = musicbrainzngs.search_releases(artist=artist, release=album, limit=3)
            for rel in res.get("release-list", []) or []:
                mbid = rel.get("id")
                if mbid:
                    url = await try_caa(mbid)
                    if url:
                        return url

        res = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=3)
        for rec in res.get("recording-list", []) or []:
            for rel in rec.get("release-list", []) or []:
                mbid = rel.get("id")
                if mbid:
                    url = await try_caa(mbid)
                    if url:
                        return url

    except Exception as e:
        logger.warn("MusicBrainz/CAA lookup failed", artist=artist, title=title, error=str(e))

    return None

async def main():
    # Database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://raido:raido_password@db:5432/raido")
    
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine)
    
    async with async_session() as session:
        # Get tracks without artwork
        result = await session.execute(
            select(Track).where(Track.artwork_url.is_(None))
        )
        tracks = result.scalars().all()
        
        logger.info(f"Found {len(tracks)} tracks without artwork")
        
        updated_count = 0
        for track in tracks:
            logger.info("Processing track", id=track.id, artist=track.artist, title=track.title)
            
            artwork_url = await lookup_artwork(track.artist, track.title, track.album)
            
            if artwork_url:
                await session.execute(
                    update(Track)
                    .where(Track.id == track.id)
                    .values(artwork_url=artwork_url)
                )
                updated_count += 1
                logger.info("Updated artwork", track_id=track.id, artwork_url=artwork_url)
            else:
                logger.info("No artwork found", track_id=track.id, artist=track.artist, title=track.title)
            
            # Small delay to be nice to iTunes API
            await asyncio.sleep(0.5)
        
        await session.commit()
        logger.info(f"Updated {updated_count} tracks with artwork")

if __name__ == "__main__":
    asyncio.run(main())
