from typing import Literal

from fastapi import APIRouter, Response, status
from geoflow_config import get_settings
from pydantic import BaseModel

from geoflow_api.db import database_is_ready
from geoflow_api.redis_client import redis_is_ready

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class DependencyStatus(BaseModel):
    status: Literal["ready", "unavailable"]


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: dict[str, DependencyStatus]


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    settings = get_settings()
    return LiveResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
async def ready(response: Response) -> ReadyResponse:
    database_ready = await database_is_ready()
    redis_ready = await redis_is_ready()
    is_ready = database_ready and redis_ready

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        status="ready" if is_ready else "degraded",
        dependencies={
            "database": DependencyStatus(
                status="ready" if database_ready else "unavailable"
            ),
            "redis": DependencyStatus(status="ready" if redis_ready else "unavailable"),
        },
    )

