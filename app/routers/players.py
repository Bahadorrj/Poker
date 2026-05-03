import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from ..db import get_async_session
from ..models import Club, GameTable, Player, User
from ..schemas import PlayerResponse
from .auth import current_active_user
from .tables import validate_permission as validate_table_permission

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
    session: AsyncSession,
):
    return await get_player_model(
        player_id,
        session,
        selectinload(Player.table)
        .selectinload(GameTable.club)
        .selectinload(Club.members),
    )


def validate_permission(user: User, player: Player):
    if not (
        user.is_superuser  # Admin
        or player.user_id == user.id  # Player himself
        or player.table.owner_id == user.id  # Table owner
        or player.table.club.owner_id == user.id  #  Club owner
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to get this player",
        )


@router.get("/{player_id}")
async def get_player(
    player_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PlayerResponse:
    player = await _get_player_model(player_id, session)

    validate_permission(user, player)

    return PlayerResponse.model_validate(player)


@router.put("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def charge_player(
    player_id: uuid.UUID,
    amount: int = Query(gt=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    player = await _get_player_model(player_id, session)

    validate_permission(user, player)

    table = player.table

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    player.buy_in += amount

    await session.commit()


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(
    player_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    player = await _get_player_model(player_id, session)

    validate_permission(user, player)

    await session.delete(player)
    await session.commit()
