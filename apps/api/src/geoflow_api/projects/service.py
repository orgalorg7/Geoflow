import uuid
from datetime import UTC, datetime
from typing import Any

from geoalchemy2.shape import from_shape, to_shape
from geoflow_config import Settings
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from geoflow_api.models import AreaOfInterest, Project
from geoflow_api.projects.geojson import (
    ValidatedPolygon,
    parse_geojson_upload,
    validate_polygon_geojson,
)
from geoflow_api.projects.repository import ProjectRepository


class ResourceNotFoundError(ValueError):
    pass


class ProjectService:
    def __init__(self, repository: ProjectRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def list_projects(self, user_id: uuid.UUID) -> list[Project]:
        return await self.repository.list_projects(user_id)

    async def get_project(
        self, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Project:
        project = await self.repository.get_project(project_id)
        if project is None or project.user_id != user_id:
            raise ResourceNotFoundError("Project not found")
        return project

    async def create_project(
        self,
        user_id: uuid.UUID,
        *,
        name: str,
        description: str | None,
    ) -> Project:
        now = datetime.now(UTC)
        project = Project(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            description=_clean_description(description),
            created_at=now,
            updated_at=now,
        )
        await self.repository.add_project(project)
        await self.repository.commit()
        return project

    async def update_project(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        name: str | None,
        description: str | None,
        description_is_set: bool,
    ) -> Project:
        project = await self.get_project(user_id, project_id)
        if name is not None:
            project.name = name
        if description_is_set:
            project.description = _clean_description(description)
        project.updated_at = datetime.now(UTC)
        await self.repository.commit()
        return project

    async def delete_project(
        self, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        project = await self.get_project(user_id, project_id)
        await self.repository.delete_project(project)
        await self.repository.commit()

    async def list_aois(
        self, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[AreaOfInterest]:
        await self.get_project(user_id, project_id)
        return await self.repository.list_aois(project_id)

    async def get_aoi(
        self, user_id: uuid.UUID, project_id: uuid.UUID, aoi_id: uuid.UUID
    ) -> AreaOfInterest:
        await self.get_project(user_id, project_id)
        aoi = await self.repository.get_aoi(aoi_id)
        if aoi is None or aoi.project_id != project_id:
            raise ResourceNotFoundError("Area of interest not found")
        return aoi

    async def create_aoi(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        name: str,
        geometry: dict[str, Any],
    ) -> AreaOfInterest:
        await self.get_project(user_id, project_id)
        validated = self._validate(geometry)
        return await self._save_new_aoi(project_id, name, validated)

    async def create_aoi_from_upload(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        name: str,
        filename: str | None,
        content_type: str | None,
        content: bytes,
    ) -> AreaOfInterest:
        await self.get_project(user_id, project_id)
        validated = parse_geojson_upload(
            filename=filename,
            content_type=content_type,
            content=content,
            max_bytes=self.settings.aoi_max_upload_bytes,
            max_vertices=self.settings.aoi_max_vertices,
            max_area_sq_km=self.settings.aoi_max_area_sq_km,
        )
        return await self._save_new_aoi(project_id, name, validated)

    async def update_aoi(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        aoi_id: uuid.UUID,
        *,
        name: str | None,
        geometry: dict[str, Any] | None,
    ) -> AreaOfInterest:
        aoi = await self.get_aoi(user_id, project_id, aoi_id)
        if name is not None:
            aoi.name = name
        if geometry is not None:
            validated = self._validate(geometry)
            aoi.geometry = from_shape(validated.polygon, srid=4326)
            aoi.area_sq_km = validated.area_sq_km
        aoi.updated_at = datetime.now(UTC)
        await self.repository.commit()
        return aoi

    async def delete_aoi(
        self, user_id: uuid.UUID, project_id: uuid.UUID, aoi_id: uuid.UUID
    ) -> None:
        aoi = await self.get_aoi(user_id, project_id, aoi_id)
        await self.repository.delete_aoi(aoi)
        await self.repository.commit()

    def serialize_aoi_geometry(self, aoi: AreaOfInterest) -> dict[str, Any]:
        geometry = aoi.geometry
        shapely_geometry = (
            geometry if isinstance(geometry, BaseGeometry) else to_shape(geometry)
        )
        return dict(mapping(shapely_geometry))

    def _validate(self, geometry: dict[str, Any]) -> ValidatedPolygon:
        return validate_polygon_geojson(
            geometry,
            max_vertices=self.settings.aoi_max_vertices,
            max_area_sq_km=self.settings.aoi_max_area_sq_km,
        )

    async def _save_new_aoi(
        self, project_id: uuid.UUID, name: str, validated: ValidatedPolygon
    ) -> AreaOfInterest:
        now = datetime.now(UTC)
        aoi = AreaOfInterest(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            geometry=from_shape(validated.polygon, srid=4326),
            area_sq_km=validated.area_sq_km,
            created_at=now,
            updated_at=now,
        )
        await self.repository.add_aoi(aoi)
        await self.repository.commit()
        return aoi


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    cleaned = description.strip()
    return cleaned or None
