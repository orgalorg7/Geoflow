import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from geoflow_config import Settings

from geoflow_api.auth.repository import AuthRepository, RepositoryConflictError
from geoflow_api.auth.security import (
    InvalidAccessTokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from geoflow_api.models import RefreshToken, User


class AuthenticationError(ValueError):
    pass


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidSessionError(ValueError):
    pass


@dataclass(frozen=True)
class SessionTokens:
    access_token: str
    refresh_token: str
    user: User


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def register(
        self, *, email: str, full_name: str, password: str
    ) -> SessionTokens:
        normalized_email = email.strip().lower()
        if await self.repository.get_user_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError("An account with this email already exists")

        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=normalized_email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="user",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await self.repository.add_user(user)
        tokens = await self._create_session(user)
        try:
            await self.repository.commit()
        except RepositoryConflictError as exc:
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists"
            ) from exc
        return tokens

    async def login(self, *, email: str, password: str) -> SessionTokens:
        user = await self.repository.get_user_by_email(email.strip().lower())
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.password_hash)
        ):
            raise AuthenticationError("Invalid email or password")

        tokens = await self._create_session(user)
        await self.repository.commit()
        return tokens

    async def refresh(self, raw_refresh_token: str) -> SessionTokens:
        now = datetime.now(UTC)
        token = await self.repository.get_refresh_token_for_update(
            hash_refresh_token(raw_refresh_token)
        )
        if token is None:
            raise InvalidSessionError("Invalid refresh token")

        if token.revoked_at is not None:
            await self.repository.revoke_refresh_family(token.user_id, token.family_id)
            await self.repository.commit()
            raise InvalidSessionError("Refresh token reuse detected")

        if token.expires_at <= now:
            token.revoked_at = now
            await self.repository.commit()
            raise InvalidSessionError("Refresh token expired")

        user = await self.repository.get_user_by_id(token.user_id)
        if user is None or not user.is_active:
            raise InvalidSessionError("User account is unavailable")

        raw_replacement = create_refresh_token()
        replacement = self._build_refresh_token(
            user_id=user.id,
            raw_token=raw_replacement,
            family_id=token.family_id,
        )
        await self.repository.add_refresh_token(replacement)
        await self.repository.flush()
        token.revoked_at = now
        token.replaced_by_id = replacement.id
        await self.repository.commit()

        return SessionTokens(
            access_token=create_access_token(user.id, self.settings),
            refresh_token=raw_replacement,
            user=user,
        )

    async def logout(self, raw_refresh_token: str | None) -> None:
        if not raw_refresh_token:
            return
        token = await self.repository.get_refresh_token_for_update(
            hash_refresh_token(raw_refresh_token)
        )
        if token is not None:
            await self.repository.revoke_refresh_family(token.user_id, token.family_id)
            await self.repository.commit()

    async def current_user(self, access_token: str) -> User:
        try:
            user_id = decode_access_token(access_token, self.settings)
        except InvalidAccessTokenError as exc:
            raise AuthenticationError("Invalid or expired access token") from exc

        user = await self.repository.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account is unavailable")
        return user

    async def _create_session(self, user: User) -> SessionTokens:
        raw_refresh_token = create_refresh_token()
        refresh_token = self._build_refresh_token(
            user_id=user.id,
            raw_token=raw_refresh_token,
            family_id=uuid.uuid4(),
        )
        await self.repository.add_refresh_token(refresh_token)
        return SessionTokens(
            access_token=create_access_token(user.id, self.settings),
            refresh_token=raw_refresh_token,
            user=user,
        )

    def _build_refresh_token(
        self, *, user_id: uuid.UUID, raw_token: str, family_id: uuid.UUID
    ) -> RefreshToken:
        return RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=self.settings.auth_refresh_token_days),
        )
