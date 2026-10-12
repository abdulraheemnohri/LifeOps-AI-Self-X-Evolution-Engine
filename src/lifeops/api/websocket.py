"""WebSocket and SSE endpoints for real-time updates."""
import asyncio
import json
import uuid
from typing import Any, Dict, Set

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
from starlette.requests import Request
from starlette.routing import Route, WebSocketRoute
from starlette.responses import StreamingResponse
import sse_starlette.sse as sse


class ConnectionManager:
    """Manage WebSocket connections for broadcasting events."""

    def __init__(self):
        self.active_connections: Set[Any] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket):
        """Add a new WebSocket connection."""
        async with self._lock:
            self.active_connections.add(websocket)

    def disconnect(self, websocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    self.active_connections.discard(connection)


class EventStreamManager:
    """Manage SSE connections for event streaming."""

    def __init__(self):
        self.active_connections: Set[Any] = set()
        self._lock = asyncio.Lock()

    async def connect(self, sse_instance):
        """Add a new SSE connection."""
        async with self._lock:
            self.active_connections.add(sse_instance)

    def disconnect(self, sse_instance):
        """Remove an SSE connection."""
        async with self._lock:
            self.active_connections.discard(sse_instance)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected SSE clients."""
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection._send(json.dumps(message))
                except Exception:
                    self.active_connections.discard(connection)


# Global managers
websocket_manager = ConnectionManager()
sse_manager = EventStreamManager()


class WebSocketEventsEndpoint(WebSocketEndpoint):
    """WebSocket endpoint for real-time event notifications."""

    encoding = "json"

    async def on_connect(self, websocket):
        """Handle new connection."""
        await websocket_manager.connect(websocket)
        await websocket.accept()
        
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "timestamp": str(uuid.uuid4())
        }))

    async def on_disconnect(self, websocket, close_code):
        """Handle disconnection."""
        websocket_manager.disconnect(websocket)

    async def on_receive(self, websocket, data):
        """Handle incoming messages (not used for broadcast-only)."""
        # Acknowledge ping messages
        if data == "ping":
            await websocket.send_text(json.dumps({"type": "pong"}))


async def sse_events_endpoint(request: Request):
    """Server-Sent Events endpoint for real-time updates."""
    async def event_stream():
        sse_instance = sse.EventSourceResponse(
            request,
            ping=30,  # Send ping every 30 seconds
            ping_message_factory=lambda: json.dumps({"type": "ping"})
        )
        
        await sse_manager.connect(sse_instance)
        
        try:
            # Send initial connection message
            await sse_instance._send(json.dumps({
                "type": "connected",
                "timestamp": str(uuid.uuid4())
            }))
            
            # Keep connection alive
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            sse_manager.disconnect(sse_instance)
        except Exception:
            sse_manager.disconnect(sse_instance)
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def broadcast_event(event_type: str, data: Dict[str, Any]):
    """Broadcast an event to all connected WebSocket and SSE clients."""
    message = {
        "type": event_type,
        "timestamp": str(uuid.uuid4()),
        "data": data
    }
    
    # Broadcast to WebSocket clients
    await websocket_manager.broadcast(message)
    
    # Broadcast to SSE clients
    await sse_manager.broadcast(message)


# Routes
websocket_route = WebSocketRoute("/ws/events", WebSocketEventsEndpoint)
sse_route = Route("/api/v1/events", sse_events_endpoint)


def get_websocket_routes():
    """Get WebSocket and SSE routes."""
    return [websocket_route, sse_route]
