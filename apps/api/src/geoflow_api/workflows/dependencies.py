from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from geoflow_api.db import get_session
from geoflow_api.workflows.repository import SqlAlchemyWorkflowRepository
from geoflow_api.workflows.service import WorkflowService


async def get_workflow_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkflowService:
    return WorkflowService(SqlAlchemyWorkflowRepository(session))
