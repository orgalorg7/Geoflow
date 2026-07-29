from typing import Annotated

from fastapi import Depends
from geoflow_config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from geoflow_api.db import get_session
from geoflow_api.projects.repository import SqlAlchemyProjectRepository
from geoflow_api.projects.service import ProjectService


async def get_project_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectService:
    return ProjectService(SqlAlchemyProjectRepository(session), get_settings())
