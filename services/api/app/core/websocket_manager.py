from typing import List, Dict, Any
from fastapi import WebSocket
import structlog
import json

logger = structlog.get_logger()

class WebSocketManager:
    """Manages WebSocket connections for live updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected", total_connections=len(self.active_connections))
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Failed to send personal message", error=str(e))
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected_clients = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error("Failed to broadcast message", error=str(e))
                disconnected_clients.append(connection)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client)
        
        if disconnected_clients:
            logger.info("Removed disconnected clients", count=len(disconnected_clients))
    
    async def broadcast_now_playing(self, track_data: Dict[str, Any]):
        """Broadcast now playing information"""
        await self.broadcast({
            "type": "now_playing",
            "data": track_data
        })
    
    async def broadcast_commentary(self, commentary_data: Dict[str, Any]):
        """Broadcast new DJ commentary"""
        await self.broadcast({
            "type": "commentary",
            "data": commentary_data
        })
    
    async def broadcast_track_change(self, track_data: Dict[str, Any]):
        """Broadcast track change event"""
        await self.broadcast({
            "type": "track_change",
            "data": track_data
        })