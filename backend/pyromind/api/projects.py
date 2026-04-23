"""Project REST routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from pyromind.api.deps import db_conn
from pyromind.catalog import repositories as repos
from pyromind.models.project import Project, ProjectCreate, ProjectDetail

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[Project])
async def list_projects(conn: sqlite3.Connection = Depends(db_conn)) -> list[Project]:
    """List all projects."""
    projects = repos.list_projects(conn)
    conn.commit()
    return projects


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    conn: sqlite3.Connection = Depends(db_conn),
) -> Project:
    """Create a new empty project."""
    project = repos.create_project(conn, body.name)
    conn.commit()
    return project


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    conn: sqlite3.Connection = Depends(db_conn),
) -> ProjectDetail:
    """Return project metadata plus show summaries."""
    detail = repos.get_project_detail(conn, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    conn.commit()
    return detail


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    conn: sqlite3.Connection = Depends(db_conn),
) -> None:
    """Delete a project and dependent shows."""
    removed = repos.delete_project(conn, project_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    conn.commit()
