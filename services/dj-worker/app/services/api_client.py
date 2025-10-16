import asyncio
from typing import Dict, Any, Optional, List
import structlog
import httpx

from app.core.config import settings

logger = structlog.get_logger()

class APIClient:
    """Client for interacting with the main Raido API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def get_now_playing(self) -> Optional[Dict[str, Any]]:
        """Get current playing track information"""
        for attempt in range(3):
            try:
                response = await self.client.get(f"{self.base_url}/api/v1/now/")
                if response.status_code == 200:
                    return response.json()
                
                if attempt < 2:  # Don't log error on final attempt
                    logger.warning("Failed to get now playing, retrying", status=response.status_code, attempt=attempt+1)
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error("Failed to get now playing after retries", status=response.status_code)
                    return None
            
            except Exception as e:
                if attempt < 2:
                    logger.warning("Error getting now playing, retrying", error=str(e), attempt=attempt+1)
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error("Error getting now playing after retries", error=str(e))
                    return None
    
    async def get_history(self, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get play history"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/now/history",
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            
            logger.error("Failed to get history", status=response.status_code)
            return None
        
        except Exception as e:
            logger.error("Error getting history", error=str(e))
            return None
    
    async def get_next_up(self) -> Optional[Dict[str, Any]]:
        """Get upcoming tracks"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/now/next")
            if response.status_code == 200:
                return response.json()
            
            logger.error("Failed to get next up", status=response.status_code)
            return None
        
        except Exception as e:
            logger.error("Error getting next up", error=str(e))
            return None
    
    async def get_settings(self) -> Optional[Dict[str, Any]]:
        """Get application settings"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/admin/settings")
            if response.status_code == 200:
                return response.json()
            
            logger.debug("Settings not available", status=response.status_code)
            return {}
        
        except Exception as e:
            logger.error("Error getting settings", error=str(e))
            return {}
    
    async def create_commentary(self, commentary_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new commentary record and return the response JSON."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/admin/commentary",
                json=commentary_data
            )
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except Exception:
                    data = {"status": "success"}
                logger.info("Commentary saved successfully")
                return data
            logger.error(
                "Failed to save commentary",
                status=response.status_code,
                response=response.text,
            )
            return None
        except Exception as e:
            logger.error("Error creating commentary", error=str(e))
            return None

    async def update_commentary(self, commentary_id: int, payload: Dict[str, Any]) -> bool:
        """Update an existing commentary record by ID."""
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/admin/commentary/{commentary_id}",
                json=payload,
            )
            if response.status_code in [200, 204]:
                return True
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            logger.error("Failed to update commentary", status=response.status_code, detail=str(detail)[:200])
            return False
        except Exception as e:
            logger.error("Error updating commentary", error=str(e))
            return False
    
    async def inject_commentary(self, audio_filename: str, station: str = "main") -> bool:
        """Tell Liquidsoap to inject commentary"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/liquidsoap/inject_commentary",
                params={"filename": audio_filename, "station": station}
            )

            if response.status_code == 200:
                logger.info("Commentary injection requested", filename=audio_filename, station=station)
                return True

            logger.error("Failed to request commentary injection",
                        status=response.status_code, station=station)
            return False

        except Exception as e:
            logger.error("Error injecting commentary", error=str(e), station=station)
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
