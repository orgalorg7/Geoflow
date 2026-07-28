import pytest
from httpx import ASGITransport, AsyncClient

from geoflow_api.main import app


@pytest.mark.asyncio
async def test_liveness_returns_service_metadata() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "GeoFlow API",
        "version": "0.1.0",
        "environment": "test",
    }


@pytest.mark.asyncio
async def test_openapi_is_available() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "GeoFlow API"
