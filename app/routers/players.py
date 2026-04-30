import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from ..db import get_async_session
from ..models import Player, User
from ..schemas import PlayerResponse
from .auth import current_active_user

router = APIRouter(prefix="/players", tags=["players"])


async def get_player_model(
    player_id: str,
    session: AsyncSession,
    *options: Any,
) -> Player:
    player_uuid = uuid.UUID(player_id)

    stmt = select(Player).where(Player.id == player_uuid)

    if options:
        stmt = stmt.options(*options)

    result = await session.execute(stmt)
    player = result.scalars().first()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    return player


@router.get("/{player_id}")
async def get_player(
    player_id: str, session: AsyncSession = Depends(get_async_session)
) -> PlayerResponse:
    return PlayerResponse.model_validate(await get_player_model(player_id, session))


@router.put("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def charge_player(
    player_id: str,
    amount: int = Query(gt=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    player = await get_player_model(player_id, session, selectinload(Player.table))
    table = player.table

    if not (
        user.is_superuser  # admin
        or player.user_id == user.id  # the player himself
        or user.id == player.table.owner_id  # table owner
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to get this player",
        )

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    player.buy_in += amount

    await session.commit()


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(
    player_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    player = await get_player_model(player_id, session)

    if not (
        user.is_superuser
        or player.user_id == user.id
        or user.id == player.table.owner_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to get this player",
        )

    await session.delete(player)
    await session.commit()
