import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from geoflow_api.models import AreaOfInterest, Project


class ProjectRepositoryConflictError(RuntimeError):
    pass


class ProjectRepository(Protocol):
    async def list_projects(self, user_id: uuid.UUID) -> list[Project]: ...

    async def get_project(self, project_id: uuid.UUID) -> Project | None: ...

    async def add_project(self, project: Project) -> None: ...

    async def delete_project(self, project: Project) -> None: ...

    async def list_aois(self, project_id: uuid.UUID) -> list[AreaOfInterest]: ...

    async def get_aoi(self, aoi_id: uuid.UUID) -> AreaOfInterest | None: ...

    async def add_aoi(self, aoi: AreaOfInterest) -> None: ...

    async def delete_aoi(self, aoi: AreaOfInterest) -> None: ...

    async def commit(self) -> None: ...


class SqlAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_projects(self, user_id: uuid.UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.updated_at.desc())
        )
        return list(result.scalars())

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def add_project(self, project: Project) -> None:
        self.session.add(project)

    async def delete_project(self, project: Project) -> None:
        await self.session.delete(project)

    async def list_aois(self, project_id: uuid.UUID) -> list[AreaOfInterest]:
        result = await self.session.execute(
            select(AreaOfInterest)
            .where(AreaOfInterest.project_id == project_id)
            .order_by(AreaOfInterest.updated_at.desc())
        )
        return list(result.scalars())

    async def get_aoi(self, aoi_id: uuid.UUID) -> AreaOfInterest | None:
        return await self.session.get(AreaOfInterest, aoi_id)

    async def add_aoi(self, aoi: AreaOfInterest) -> None:
        self.session.add(aoi)

    async def delete_aoi(self, aoi: AreaOfInterest) -> None:
        await self.session.delete(aoi)

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProjectRepositoryConflictError from exc
