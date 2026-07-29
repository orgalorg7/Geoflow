import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean_required_name(value)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return _clean_required_name(value) if value is not None else None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AOICreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    geometry: dict[str, Any]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean_required_name(value)


class AOIUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    geometry: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return _clean_required_name(value) if value is not None else None


class AOIResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    geometry: dict[str, Any]
    area_sq_km: float
    created_at: datetime
    updated_at: datetime


def _clean_required_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < 2:
        raise ValueError("Name must contain at least 2 characters")
    return cleaned
