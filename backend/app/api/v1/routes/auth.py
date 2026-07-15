import logging
import smtplib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    PasswordResetTokenError,
    RefreshTokenError,
    create_access_token,
    create_refresh_token,
    request_password_reset,
    reset_password,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.auth.email_delivery import deliver_password_reset
from app.auth.rate_limit import enforce_auth_rate_limit
from app.db.session import get_db_session
from app.schemas.auth import (
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.users.service import authenticate_user

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


@router.post(
    "/token",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def create_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    user = await authenticate_user(session, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    refresh_token = await create_refresh_token(session, user)
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    try:
        user, new_refresh_token = await rotate_refresh_token(session, payload.refresh_token)
    except RefreshTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=new_refresh_token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def logout(
    payload: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await revoke_refresh_token(session, payload.refresh_token)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def create_password_reset_request(
    payload: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    issue = await request_password_reset(session, str(payload.email))
    if issue is not None:
        try:
            _ = await deliver_password_reset(issue)
        except (OSError, smtplib.SMTPException) as e:
            logger.exception("Password reset delivery failed", exc_info=e)
    return MessageResponse(
        message="If an account exists for this email, password reset instructions will be sent."
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    try:
        _ = await reset_password(session, payload.reset_token, payload.new_password)
    except PasswordResetTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return MessageResponse(message="Password has been reset.")
