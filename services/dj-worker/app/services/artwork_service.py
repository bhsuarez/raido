import asyncio
import hashlib
from typing import Optional, Dict, Any
import structlog
import httpx
import json

logger = structlog.get_logger()

class ArtworkService:
    """Service for looking up album artwork from various sources"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.cache = {}  # Simple in-memory cache
    
    async def get_artwork_url(self, artist: str, title: str, album: Optional[str] = None) -> Optional[str]:
        """Get artwork URL for a track"""
        
        # Create cache key
        cache_key = hashlib.md5(f"{artist}_{title}_{album or ''}".lower().encode()).hexdigest()
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try multiple sources
        artwork_url = None
        
        # Try iTunes API first (free, no auth required)
        artwork_url = await self._lookup_itunes(artist, title, album)
        
        if not artwork_url:
            # Try MusicBrainz + Cover Art Archive
            artwork_url = await self._lookup_musicbrainz(artist, title, album)
        
        # Cache the result (even if None to avoid repeat lookups)
        self.cache[cache_key] = artwork_url
        
        if artwork_url:
            logger.debug("Found artwork", artist=artist, title=title, url=artwork_url)
        else:
            logger.debug("No artwork found", artist=artist, title=title)
            
        return artwork_url
    
    async def _lookup_itunes(self, artist: str, title: str, album: Optional[str] = None) -> Optional[str]:
        """Lookup artwork using iTunes Search API"""
        try:
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
                "limit": 5
            }
            
            response = await self.client.get("https://itunes.apple.com/search", params=params)
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
                        return artwork_url
            
            return None
            
        except Exception as e:
            logger.debug("iTunes lookup failed", error=str(e))
            return None
    
    async def _lookup_musicbrainz(self, artist: str, title: str, album: Optional[str] = None) -> Optional[str]:
        """Lookup artwork using MusicBrainz + Cover Art Archive"""
        try:
            # First, search for the release
            search_query = f"artist:{artist}"
            if album:
                search_query += f" AND release:{album}"
            else:
                search_query += f" AND recording:{title}"
            
            headers = {
                "User-Agent": "Raido/1.0 (https://raido.local)"
            }
            
            params = {
                "query": search_query,
                "fmt": "json",
                "limit": 3
            }
            
            response = await self.client.get(
                "https://musicbrainz.org/ws/2/release",
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            releases = data.get("releases", [])
            
            for release in releases:
                mbid = release.get("id")
                if mbid:
                    # Try to get cover art from Cover Art Archive
                    cover_response = await self.client.get(
                        f"https://coverartarchive.org/release/{mbid}",
                        headers=headers
                    )
                    
                    if cover_response.status_code == 200:
                        cover_data = cover_response.json()
                        images = cover_data.get("images", [])
                        
                        for image in images:
                            if image.get("front"):  # Front cover
                                return image.get("image")
            
            return None
            
        except Exception as e:
            logger.debug("MusicBrainz lookup failed", error=str(e))
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()