import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from .auth import current_active_user
from .tables import get_table_model
from ..db import get_async_session
from ..models import Player, User
from ..schemas import PlayerResponse

router = APIRouter(prefix="/players", tags=["players"])


@router.post("/{table_id}", status_code=status.HTTP_201_CREATED)
async def join_table(
    table_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> uuid.UUID:
    table = await get_table_model(table_id, session)

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    player = Player(user_id=user.id, table_id=table.id)
    session.add(player)

    await session.commit()
    await session.refresh(player)

    return player.id


async def get_player_model(
    player_id: str,
    session: AsyncSession,
) -> Player:
    player_uuid = uuid.UUID(player_id)

    result = await session.execute(
        select(Player)
        .where(Player.id == player_uuid)
        .options(selectinload(Player.table), selectinload(Player.user))
    )
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
    player = await get_player_model(player_id, session)

    return PlayerResponse.model_validate(player)


@router.put("/{player_id}/charge", status_code=status.HTTP_204_NO_CONTENT)
async def charge_player(
    player_id: str,
    amount: int = Query(gt=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    player = await get_player_model(player_id, session)
    table = player.table

    if not (
        user.is_superuser  # admin
        or player.user_id == user.id  # the player himself
        or user.id == player.table.user_id  # table owner
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


@router.put("/{player_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_table(
    player_id: str,
    cash_out: int = Query(ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    player = await get_player_model(player_id, session)

    if not player.is_playing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Player already left"
        )

    if not (
        user.is_superuser
        or player.user_id == user.id
        or user.id == player.table.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to get this player",
        )

    table = player.table

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    player.cash_out = cash_out
    player.is_playing = False

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
        or user.id == player.table.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to get this player",
        )

    await session.delete(player)
    await session.commit()
