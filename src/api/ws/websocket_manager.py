import threading

from typing import Dict, Set, Optional
from fastapi import WebSocket

class WebSocketManager:
    """WebSocket manager thread-safe"""
    
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._lock = threading.RLock()
    
    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self._connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        with self._lock:
            self._connections.pop(client_id, None)
            
    async def send_personal_message(self, message: dict, client_id: str):
        with self._lock:
            websocket = self._connections.get(client_id)
        
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(client_id)
    
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None):
        exclude = exclude or set()
        
        with self._lock:
            connections = list(self._connections.items())
        
        for client_id, websocket in connections:
            if client_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception:
                    self.disconnect(client_id)
    
    def get_active_connections_count(self) -> int:
        with self._lock:
            return len(self._connections)
    
    def get_connected_clients(self) -> list[str]:
        with self._lock:
            return list(self._connections.keys())
