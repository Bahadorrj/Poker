import uuid
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from starlette import status

from ..db import get_async_session
from ..models import GameTable, User, Player
from ..schemas import (
    UserRead,
    UserUpdate,
    UserHistoryResponse,
    PlayerResponse,
)

from .auth import fastapi_users, current_active_user

router = APIRouter()


@router.get("/users", tags=["users"])
async def get_users(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[UserRead]:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can not get all users",
        )

    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users: list[User] = [row[0] for row in result.all()]

    return [
        UserRead(
            id=u.id,
            username=u.username,
            email=u.email,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            is_verified=u.is_verified,
        )
        for u in users
    ]


user_router = APIRouter(prefix="/users", tags=["users"])
user_router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))


async def get_history_response(session: AsyncSession, user: User):
    # Net balance
    result = await session.execute(
        select(Player).filter_by(user_id=user.id).options(selectinload(Player.table))
    )
    players = result.scalars().all()
    net_balance = sum(p.cash_out - p.buy_in for p in players)

    # Time
    tables = [p.table for p in players]
    time_delta = datetime.timedelta()
    for g in tables:
        if not g.finished:
            continue

        if g.finished_at is None:
            raise ValueError("invalid finish time")

        time_delta += g.finished_at - g.started_at

    hours, rest = divmod(time_delta, datetime.timedelta(hours=1))
    minutes, rest = divmod(rest, datetime.timedelta(minutes=1))
    seconds = rest.seconds
    total_time = datetime.time(hour=hours, minute=minutes, second=seconds)

    history = [PlayerResponse.model_validate(p) for p in players]

    return UserHistoryResponse(
        history=history,
        net_balance=net_balance,
        total_time=total_time,
    )


@user_router.get("/me/history")
async def get_history(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> UserHistoryResponse:
    return await get_history_response(session, user)


@user_router.get("/leaderboard")
async def get_leaderboard(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> dict[str, int]:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to get the leaderboard",
        )

    result = await session.execute(
        select(GameTable)
        .where(GameTable.finished)
        .options(selectinload(GameTable.players))
    )
    tables = result.scalars().all()

    leaderboard: dict[str, int] = {}

    for table in tables:
        if not table.finished:
            continue

        for player in table.players:
            username = player.username

            if username not in leaderboard:
                leaderboard[username] = 0

            net_balance = player.cash_out - player.buy_in
            leaderboard[username] += net_balance

    return dict(sorted(leaderboard.items(), key=lambda item: item[1]))


router.include_router(user_router)
