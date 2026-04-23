"""HTTP tests for project CRUD routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_create_project(client: TestClient) -> None:
    """POST /projects creates a row with an id."""
    response = client.post("/projects", json={"name": "Test Project"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Project"
    assert "id" in body


def test_list_projects(client: TestClient) -> None:
    """GET /projects returns created rows."""
    client.post("/projects", json={"name": "Alpha"})
    client.post("/projects", json={"name": "Beta"})
    rows = client.get("/projects").json()
    names = {p["name"] for p in rows}
    assert "Alpha" in names and "Beta" in names


def test_get_project_detail(client: TestClient) -> None:
    """GET /projects/{id} includes nested shows list."""
    created = client.post("/projects", json={"name": "Detail"}).json()
    detail = client.get(f"/projects/{created['id']}").json()
    assert detail["name"] == "Detail"
    assert "shows" in detail
    assert isinstance(detail["shows"], list)


def test_delete_project(client: TestClient) -> None:
    """DELETE removes the project."""
    created = client.post("/projects", json={"name": "ToDelete"}).json()
    deleted = client.delete(f"/projects/{created['id']}")
    assert deleted.status_code == 204
    missing = client.get(f"/projects/{created['id']}")
    assert missing.status_code == 404
