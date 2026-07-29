import uuid
from datetime import UTC, datetime

import pytest
from geoflow_config import Settings
from httpx import ASGITransport, AsyncClient

from geoflow_api.auth.dependencies import get_current_user
from geoflow_api.main import app
from geoflow_api.models import AreaOfInterest, Project, User
from geoflow_api.projects.dependencies import get_project_service
from geoflow_api.projects.repository import ProjectRepository
from geoflow_api.projects.service import ProjectService, ResourceNotFoundError


class InMemoryProjectRepository(ProjectRepository):
    def __init__(self) -> None:
        self.projects: dict[uuid.UUID, Project] = {}
        self.aois: dict[uuid.UUID, AreaOfInterest] = {}

    async def list_projects(self, user_id: uuid.UUID) -> list[Project]:
        return [project for project in self.projects.values() if project.user_id == user_id]

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        return self.projects.get(project_id)

    async def add_project(self, project: Project) -> None:
        self.projects[project.id] = project

    async def delete_project(self, project: Project) -> None:
        self.projects.pop(project.id, None)
        self.aois = {
            key: aoi
            for key, aoi in self.aois.items()
            if aoi.project_id != project.id
        }

    async def list_aois(self, project_id: uuid.UUID) -> list[AreaOfInterest]:
        return [aoi for aoi in self.aois.values() if aoi.project_id == project_id]

    async def get_aoi(self, aoi_id: uuid.UUID) -> AreaOfInterest | None:
        return self.aois.get(aoi_id)

    async def add_aoi(self, aoi: AreaOfInterest) -> None:
        self.aois[aoi.id] = aoi

    async def delete_aoi(self, aoi: AreaOfInterest) -> None:
        self.aois.pop(aoi.id, None)

    async def commit(self) -> None:
        pass


def make_user(email: str) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email=email,
        full_name="Project Owner",
        password_hash="not-used",
        role="user",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_project_crud_is_scoped_to_owner() -> None:
    repository = InMemoryProjectRepository()
    service = ProjectService(repository, Settings(_env_file=None))
    owner = make_user("owner@example.com")
    other_user = make_user("other@example.com")

    project = await service.create_project(
        owner.id, name="Nile Delta", description="Vegetation monitoring"
    )
    assert (await service.list_projects(owner.id)) == [project]
    assert await service.list_projects(other_user.id) == []

    with pytest.raises(ResourceNotFoundError, match="Project not found"):
        await service.get_project(other_user.id, project.id)

    updated = await service.update_project(
        owner.id,
        project.id,
        name="Nile Delta 2026",
        description=None,
        description_is_set=True,
    )
    assert updated.name == "Nile Delta 2026"
    assert updated.description is None

    await service.delete_project(owner.id, project.id)
    assert await service.list_projects(owner.id) == []


@pytest.mark.asyncio
async def test_cross_user_api_access_returns_not_found() -> None:
    repository = InMemoryProjectRepository()
    service = ProjectService(repository, Settings(_env_file=None))
    owner = make_user("owner@example.com")
    other_user = make_user("other@example.com")
    active_user = {"value": owner}

    async def override_user() -> User:
        return active_user["value"]

    async def override_service() -> ProjectService:
        return service

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_project_service] = override_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/api/v1/projects",
                json={"name": "Nile Delta", "description": "Owned project"},
            )
            assert created.status_code == 201
            project_id = created.json()["id"]

            active_user["value"] = other_user
            forbidden_read = await client.get(f"/api/v1/projects/{project_id}")
            forbidden_delete = await client.delete(f"/api/v1/projects/{project_id}")

        assert forbidden_read.status_code == 404
        assert forbidden_delete.status_code == 404
    finally:
        app.dependency_overrides.clear()
