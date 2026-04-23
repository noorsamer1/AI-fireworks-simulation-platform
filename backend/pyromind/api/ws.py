"""WebSocket connection manager — per-show, never cross-show."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Track active WebSocket clients keyed by ``show_id``."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, show_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(show_id, []).append(ws)
        n = len(self._connections.get(show_id, []))
        logger.info("[WS] client connected to show %s (total: %d)", show_id, n)

    async def disconnect(self, show_id: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(show_id, [])
            if ws in conns:
                conns.remove(ws)
            if not conns:
                self._connections.pop(show_id, None)

    async def broadcast(self, show_id: str, data: dict) -> None:
        """Send JSON to every client watching ``show_id``; drop broken sockets."""
        conns = list(self._connections.get(show_id, []))
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(show_id, ws)


manager = ConnectionManager()


@router.websocket("/ws/shows/{show_id}")
async def show_websocket(show_id: str, websocket: WebSocket) -> None:
    """Stream show progress; sends DB snapshot on connect, then periodic pings."""
    from pyromind.api.shows import get_show_state_json

    await manager.connect(show_id, websocket)
    try:
        current = await get_show_state_json(show_id)
        if current:
            await websocket.send_json({"event_type": "state_sync", "data": current})
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"event_type": "ping"})
    except WebSocketDisconnect:
        await manager.disconnect(show_id, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.error("[WS] error on show %s: %s", show_id, exc)
        await manager.disconnect(show_id, websocket)
