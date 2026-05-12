import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from .auth import current_active_user
from .tables import member_permission, super_permission
from ..db import get_async_session
from ..models import Club, GameTable, Player, User
from ..schemas import PlayerResponse, PlayerUpdate

router = APIRouter(prefix="/players", tags=["players"])


async def get_player_model(
    player_id: uuid.UUID,
    session: AsyncSession,
    *options: Any,
) -> Player:
    stmt = select(Player).where(Player.id == player_id)

    if options:
        stmt = stmt.options(*options)

    result = await session.execute(stmt)
    player = result.scalars().first()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    return player


async def _get_player_model(
    player_id: uuid.UUID,
    permission: Callable,
    user: User,
    session: AsyncSession,
) -> Player:
    player = await get_player_model(
        player_id,
        session,
        selectinload(Player.table)
        .selectinload(GameTable.club)
        .selectinload(Club.members),
    )

    if permission:
        permission(user, player.table)

    return player


@router.get("/{player_id}")
async def get_player(
    player_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PlayerResponse:
    player = await _get_player_model(player_id, member_permission, user, session)

    return PlayerResponse.model_validate(player)


@router.patch("/{player_id}")
async def update_player(
    player_id: uuid.UUID,
    player_update: PlayerUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    player = await _get_player_model(player_id, super_permission, user, session)

    player.cash_out = player_update.cash_out

    await session.commit()


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(
    player_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    player = await _get_player_model(player_id, super_permission, user, session)

    await session.delete(player)
    await session.commit()
