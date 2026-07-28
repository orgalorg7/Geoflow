from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from geoflow_config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from geoflow_api.auth.repository import SqlAlchemyAuthRepository
from geoflow_api.auth.service import AuthenticationError, AuthService
from geoflow_api.db import get_session
from geoflow_api.models import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    return AuthService(SqlAlchemyAuthRepository(session), get_settings())


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    settings = get_settings()
    access_token = (
        credentials.credentials
        if credentials is not None and credentials.scheme.lower() == "bearer"
        else request.cookies.get(settings.auth_access_cookie_name)
    )
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await service.current_user(access_token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[User, Depends(get_current_user)]
