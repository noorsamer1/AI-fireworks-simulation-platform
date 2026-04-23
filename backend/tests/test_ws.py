"""WebSocket connection manager tests."""

from __future__ import annotations

import pytest

from pyromind.api.ws import ConnectionManager, manager


class FakeWebSocket:
    """Minimal WebSocket stand-in for manager unit tests."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


@pytest.fixture(autouse=True)
def _clear_singleton_manager() -> None:
    manager._connections.clear()
    yield
    manager._connections.clear()


@pytest.mark.asyncio
async def test_manager_connect_disconnect() -> None:
    m = ConnectionManager()
    ws = FakeWebSocket()
    await m.connect("show-a", ws)
    assert "show-a" in m._connections
    assert len(m._connections["show-a"]) == 1
    await m.disconnect("show-a", ws)
    assert "show-a" not in m._connections


@pytest.mark.asyncio
async def test_manager_broadcast() -> None:
    m = ConnectionManager()
    w1 = FakeWebSocket()
    w2 = FakeWebSocket()
    await m.connect("show-x", w1)
    await m.connect("show-x", w2)
    payload = {"event_type": "ping", "n": 1}
    await m.broadcast("show-x", payload)
    assert w1.sent == [payload]
    assert w2.sent == [payload]


@pytest.mark.asyncio
async def test_manager_cross_show_isolation() -> None:
    wa = FakeWebSocket()
    wb = FakeWebSocket()
    await manager.connect("show_a", wa)
    await manager.connect("show_b", wb)
    await manager.broadcast("show_a", {"event_type": "only_a"})
    assert wa.sent == [{"event_type": "only_a"}]
    assert wb.sent == []
