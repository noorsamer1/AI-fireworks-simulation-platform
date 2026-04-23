"""Project API models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pyromind.models.show import ShowSummary


class ProjectBase(BaseModel):
    """Shared project fields."""

    name: str


class ProjectCreate(ProjectBase):
    """Create-project request body."""

    pass


class Project(ProjectBase):
    """Project row for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    site_config_json: dict[str, Any]
    default_language: str


class ProjectDetail(Project):
    """Project with nested show summaries."""

    shows: list[ShowSummary] = Field(default_factory=list)
