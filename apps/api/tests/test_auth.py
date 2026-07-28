import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from geoflow_config import Settings
from httpx import ASGITransport, AsyncClient

from geoflow_api.auth.dependencies import get_auth_service
from geoflow_api.auth.repository import AuthRepository
from geoflow_api.auth.security import hash_password, verify_password
from geoflow_api.auth.service import AuthService
from geoflow_api.main import app
from geoflow_api.models import RefreshToken, User


class InMemoryAuthRepository(AuthRepository):
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.tokens: dict[str, RefreshToken] = {}

    async def get_user_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    async def add_user(self, user: User) -> None:
        self.users[user.id] = user

    async def get_refresh_token_for_update(
        self, token_hash: str
    ) -> RefreshToken | None:
        return self.tokens.get(token_hash)

    async def add_refresh_token(self, token: RefreshToken) -> None:
        self.tokens[token.token_hash] = token

    async def flush(self) -> None:
        pass

    async def revoke_refresh_family(
        self, user_id: uuid.UUID, family_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        for token in self.tokens.values():
            if (
                token.user_id == user_id
                and token.family_id == family_id
                and token.revoked_at is None
            ):
                token.revoked_at = now

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


@pytest.fixture
def repository() -> InMemoryAuthRepository:
    return InMemoryAuthRepository()


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="test-secret-that-is-long-and-random-enough",
    )


@pytest.fixture
async def client(
    repository: InMemoryAuthRepository, auth_settings: Settings
) -> AsyncIterator[AsyncClient]:
    service = AuthService(repository, auth_settings)

    async def override_auth_service() -> AuthService:
        return service

    app.dependency_overrides[get_auth_service] = override_auth_service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_registration_creates_account_and_session(
    client: AsyncClient, repository: InMemoryAuthRepository
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "Person@Example.com",
            "full_name": "Geo Flow",
            "password": "a-secure-password",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "person@example.com"
    assert response.json()["user"]["role"] == "user"
    assert "geoflow_access" in response.cookies
    assert "geoflow_refresh" in response.cookies
    user = next(iter(repository.users.values()))
    assert user.password_hash != "a-secure-password"
    assert verify_password("a-secure-password", user.password_hash)
    stored_token = next(iter(repository.tokens.values()))
    assert stored_token.token_hash != response.cookies["geoflow_refresh"]


@pytest.mark.asyncio
async def test_duplicate_registration_is_rejected(client: AsyncClient) -> None:
    payload = {
        "email": "person@example.com",
        "full_name": "Geo Flow",
        "password": "a-secure-password",
    }
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(
    client: AsyncClient, repository: InMemoryAuthRepository
) -> None:
    now = datetime.now(UTC)
    user = User(
        id=uuid.uuid4(),
        email="person@example.com",
        full_name="Geo Flow",
        password_hash=hash_password("correct-password"),
        role="user",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    repository.users[user.id] = user

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_current_user_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


@pytest.mark.asyncio
async def test_access_cookie_opens_protected_routes(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Geo Flow",
            "password": "a-secure-password",
        },
    )

    me_response = await client.get("/api/v1/auth/me")
    protected_response = await client.get("/api/v1/auth/protected")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "person@example.com"
    assert protected_response.status_code == 200
    assert protected_response.json()["message"] == "Welcome back, Geo Flow"


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_rejects_reuse(
    client: AsyncClient, repository: InMemoryAuthRepository
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Geo Flow",
            "password": "a-secure-password",
        },
    )
    original_refresh = client.cookies["geoflow_refresh"]

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    rotated_refresh = client.cookies["geoflow_refresh"]
    assert rotated_refresh != original_refresh
    assert len(repository.tokens) == 2

    client.cookies.set(
        "geoflow_refresh",
        original_refresh,
        domain="test.local",
        path="/api/v1/auth",
    )
    reused = await client.post("/api/v1/auth/refresh")

    assert reused.status_code == 401
    assert reused.json()["detail"] == "Refresh token reuse detected"
    assert "geoflow_access" not in client.cookies
    assert "geoflow_refresh" not in client.cookies
    assert all(token.revoked_at is not None for token in repository.tokens.values())


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookies(
    client: AsyncClient, repository: InMemoryAuthRepository
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Geo Flow",
            "password": "a-secure-password",
        },
    )

    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert "geoflow_access" not in client.cookies
    assert "geoflow_refresh" not in client.cookies
    assert all(token.revoked_at is not None for token in repository.tokens.values())
    assert (await client.get("/api/v1/auth/me")).status_code == 401
