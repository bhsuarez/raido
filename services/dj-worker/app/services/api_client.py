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
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/now/")
            if response.status_code == 200:
                return response.json()
            
            logger.error("Failed to get now playing", status=response.status_code)
            return None
        
        except Exception as e:
            logger.error("Error getting now playing", error=str(e))
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
    
    async def create_commentary(self, commentary_data: Dict[str, Any]) -> bool:
        """Create a new commentary record"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/admin/commentary",
                json=commentary_data
            )
            
            if response.status_code in [200, 201]:
                logger.info("Commentary saved successfully")
                return True
            
            logger.error("Failed to save commentary", 
                        status=response.status_code,
                        response=response.text)
            return False
        
        except Exception as e:
            logger.error("Error creating commentary", error=str(e))
            return False
    
    async def inject_commentary(self, audio_filename: str) -> bool:
        """Tell Liquidsoap to inject commentary"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/liquidsoap/inject_commentary",
                params={"filename": audio_filename}
            )
            
            if response.status_code == 200:
                logger.info("Commentary injection requested", filename=audio_filename)
                return True
            
            logger.error("Failed to request commentary injection", 
                        status=response.status_code)
            return False
        
        except Exception as e:
            logger.error("Error injecting commentary", error=str(e))
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()