"""HTTP tests for the effects catalog API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """The sidecar health endpoint should always return OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_effects(client: TestClient) -> None:
    """List endpoint returns paginated envelope."""
    response = client.get("/effects", params={"limit": 10})
    assert response.status_code == 200
    body = response.json()
    assert "items" in body and "total" in body
    assert len(body["items"]) == 10
    assert body["total"] == 50


def test_get_effect_by_id(client: TestClient) -> None:
    """Fetch a single effect by primary key."""
    listed = client.get("/effects", params={"limit": 1}).json()
    effect_id = listed["items"][0]["id"]
    got = client.get(f"/effects/{effect_id}")
    assert got.status_code == 200
    assert got.json()["id"] == effect_id


def test_search_by_family(client: TestClient) -> None:
    """Filter catalog rows by family."""
    response = client.get("/effects", params={"family": "shell", "limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert all(item["family"] == "shell" for item in body["items"])


def test_search_by_color(client: TestClient) -> None:
    """Filter by a color token present in the JSON colors array."""
    response = client.get("/effects", params={"color": "gold", "limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    for item in body["items"]:
        colors = [c.lower() for c in item["colors"]]
        assert "gold" in colors


def test_semantic_search_returns_ranked(client: TestClient) -> None:
    """FTS5 placeholder search returns scored rows."""
    response = client.post(
        "/effects/search/semantic",
        json={"query": "gold peony", "limit": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    if len(payload) > 0:
        assert "score" in payload[0] and "why" in payload[0] and "effect" in payload[0]


@pytest.mark.asyncio
async def test_list_effects_async(client: TestClient) -> None:
    """Async smoke using httpx against the ASGI app."""
    assert client.get("/health").status_code == 200
    from pyromind.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/effects", params={"limit": 5})
    assert response.status_code == 200
    assert response.json()["total"] == 50
