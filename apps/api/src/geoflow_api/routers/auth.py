from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from geoflow_config import Settings, get_settings
from starlette.responses import JSONResponse

from geoflow_api.auth.dependencies import CurrentUser, get_auth_service
from geoflow_api.auth.service import (
    AuthenticationError,
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidSessionError,
    SessionTokens,
)
from geoflow_api.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def set_session_cookies(
    response: Response, tokens: SessionTokens, settings: Settings
) -> None:
    common = {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": "lax",
        "domain": settings.auth_cookie_domain,
    }
    response.set_cookie(
        settings.auth_access_cookie_name,
        tokens.access_token,
        max_age=settings.auth_access_token_minutes * 60,
        path="/",
        **common,
    )
    response.set_cookie(
        settings.auth_refresh_cookie_name,
        tokens.refresh_token,
        max_age=settings.auth_refresh_token_days * 24 * 60 * 60,
        path="/api/v1/auth",
        **common,
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.auth_access_cookie_name,
        path="/",
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        settings.auth_refresh_cookie_name,
        path="/api/v1/auth",
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    try:
        tokens = await service.register(
            email=str(payload.email),
            full_name=payload.full_name,
            password=payload.password,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    set_session_cookies(response, tokens, get_settings())
    return AuthResponse(user=UserResponse.model_validate(tokens.user))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    try:
        tokens = await service.login(email=str(payload.email), password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    set_session_cookies(response, tokens, get_settings())
    return AuthResponse(user=UserResponse.model_validate(tokens.user))


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse | Response:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    try:
        tokens = await service.refresh(refresh_token)
    except InvalidSessionError as exc:
        error_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
        )
        clear_session_cookies(error_response, settings)
        return error_response
    set_session_cookies(response, tokens, settings)
    return AuthResponse(user=UserResponse.model_validate(tokens.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    settings = get_settings()
    await service.logout(request.cookies.get(settings.auth_refresh_cookie_name))
    clear_session_cookies(response, settings)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.get("/protected", response_model=MessageResponse)
async def protected(user: CurrentUser) -> MessageResponse:
    return MessageResponse(message=f"Welcome back, {user.full_name}")
