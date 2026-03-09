import os
import uuid

from fastapi import APIRouter, Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from ..db import get_user_db
from ..models import User
from ..schemas import UserCreate, UserRead


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise EnvironmentError(f"Required environment variable '{key}' is not set")
    return value


def _require_env_int(key: str) -> int:
    value = _require_env(key)
    try:
        return int(value)
    except ValueError:
        raise EnvironmentError(
            f"Environment variable '{key}' must be an integer, got: {value!r}"
        )


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = _require_env("RESET_PASSWORD_SECRET")
    reset_password_token_lifetime_seconds = (
        _require_env_int("RESET_PASSWORD_TOKEN_LIFETIME_HOURS") * 3600
    )

    verification_token_secret = _require_env("VERIFICATION_SECRET")
    verification_token_lifetime_seconds = (
        _require_env_int("VERIFICATION_TOKEN_LIFETIME_HOURS") * 3600
    )

    async def on_after_register(self, user: User, request=None):
        print(f"User {user.id} registered.")  # TODO: replace with real logging

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        print(f"Password reset token for {user.id}: {token}")  # TODO: send email here

    async def on_after_request_verify(self, user: User, token: str, request=None):
        print(f"Verification token for {user.id}: {token}")  # TODO: send email here


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db=user_db)


# Transport definition
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


# JWT strategy
def get_jwt_strategy():
    return JWTStrategy(
        secret=_require_env("JWT_SECRET"),
        lifetime_seconds=_require_env_int("JWT_LIFETIME_HOURS") * 3600,
    )  # Three hours


# Auth backend
auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

# User manager
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)

# Routers
router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)
router.include_router(
    fastapi_users.get_reset_password_router(),
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
)
