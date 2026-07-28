import uuid
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from geoflow_api.models import RefreshToken, User


class RepositoryConflictError(RuntimeError):
    pass


class AuthRepository(Protocol):
    async def get_user_by_email(self, email: str) -> User | None: ...

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None: ...

    async def add_user(self, user: User) -> None: ...

    async def get_refresh_token_for_update(
        self, token_hash: str
    ) -> RefreshToken | None: ...

    async def add_refresh_token(self, token: RefreshToken) -> None: ...

    async def flush(self) -> None: ...

    async def revoke_refresh_family(
        self, user_id: uuid.UUID, family_id: uuid.UUID
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class SqlAlchemyAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def add_user(self, user: User) -> None:
        self.session.add(user)

    async def get_refresh_token_for_update(
        self, token_hash: str
    ) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def add_refresh_token(self, token: RefreshToken) -> None:
        self.session.add(token)

    async def flush(self) -> None:
        await self.session.flush()

    async def revoke_refresh_family(
        self, user_id: uuid.UUID, family_id: uuid.UUID
    ) -> None:
        from datetime import UTC, datetime

        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise RepositoryConflictError from exc

    async def rollback(self) -> None:
        await self.session.rollback()


AuthRepositoryFactory = Callable[[AsyncSession], AuthRepository]
