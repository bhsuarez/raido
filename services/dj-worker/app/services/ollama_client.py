import asyncio
from typing import Optional
import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger()

class OllamaClient:
    """Client for Ollama API interactions"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_commentary(
        self, 
        prompt: str, 
        max_tokens: int = 200,
        temperature: float = 0.8,
        model: Optional[str] = None
    ) -> Optional[str]:
        """Generate DJ commentary text using Ollama"""
        try:
            # Use provided model or fall back to default
            use_model = model or self.model
            
            logger.debug("Generating commentary with Ollama", 
                        model=use_model,
                        max_tokens=max_tokens)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": use_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "response" in result:
                        content = result["response"].strip()
                        logger.debug("Generated commentary", length=len(content))
                        return content
                else:
                    logger.error("Ollama API error", status=response.status_code, response=response.text)
            
            return None
        
        except Exception as e:
            logger.error("Ollama commentary generation failed", error=str(e))
            raise
