"""WebSocket connection manager for real-time video and telemetry streaming."""

import asyncio
import json
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active client WebSockets and broadcasts frames concurrently."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcasts payload to all connected clients; drops disconnected ones."""
        if not self.active_connections:
            return

        dead_connections = set()
        text_data = json.dumps(data)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text_data)
            except (WebSocketDisconnect, RuntimeError):
                dead_connections.add(connection)
            except Exception as e:
                logger.warning(f"Error sending frame to WebSocket client: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def dispatch_from_thread(self, data: Dict[str, Any]):
        """Thread-safe dispatch from pipeline worker thread to asyncio event loop."""
        if self.loop and self.loop.is_running() and self.active_connections:
            asyncio.run_coroutine_threadsafe(self.broadcast_json(data), self.loop)


manager = ConnectionManager()

