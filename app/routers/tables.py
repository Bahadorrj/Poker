import datetime
import uuid
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from app.routers.players import get_player_model

from ..db import get_async_session
from ..models import Club, GameTable, Player, User
from ..schemas import (
    PlayerResponse,
    ResultResponse,
    TableResponse,
    TransactionResponse,
)
from .auth import current_active_user

router = APIRouter(prefix="/tables", tags=["tables"])


async def get_table_model(
    table_id: uuid.UUID,
    session: AsyncSession,
    *options: Any,
) -> GameTable:
    stmt = select(GameTable).where(GameTable.id == table_id)

    if options:
        stmt = stmt.options(*options)

    result = await session.execute(stmt)
    table = result.scalars().first()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Table not found"
        )

    return table


async def _get_table_model(table_id: uuid.UUID, session: AsyncSession):
    return await get_table_model(
        table_id,
        session,
        selectinload(GameTable.club).selectinload(Club.members),
        selectinload(GameTable.owner),
        selectinload(GameTable.players).selectinload(Player.user),
    )


def validate_permission(user: User, table: GameTable):
    if (
        not user.is_superuser  # Admin
        and table.owner_id != user.id  # Table owner
        and table.club.owner_id != user.id  # Club owner
        and user not in table.club.members
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to close this table",
        )


@router.get("/{table_id}")
async def get_table(
    table_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> TableResponse:
    table = await _get_table_model(table_id, session)

    validate_permission(user, table)

    return TableResponse.model_validate(table)


@router.put("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_table(
    table_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    table = await _get_table_model(table_id, session)

    validate_permission(user, table)

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    table.finished = True
    table.finished_at = datetime.datetime.now()

    # Force players to stop playing
    players = table.players
    for p in players:
        if p.is_playing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Player with username {p.username} must first leave the table",
            )

    await session.commit()


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    table = await _get_table_model(table_id, session)

    if (
        not user.is_superuser  # Admin
        and table.owner_id != user.id  # Table owner
        and table.club.owner_id != user.id  # Club owner
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this table",
        )

    await session.delete(table)
    await session.commit()


@router.post("/{table_id}/players", status_code=status.HTTP_201_CREATED)
async def join_table(
    table_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> uuid.UUID:
    table = await _get_table_model(table_id, session)

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    # Check player does not exist
    existing = await session.scalar(
        select(Player).where(
            Player.user_id == user.id, Player.table_id == table.id
        )  # Ensure the user is a player in a specified table not just a player
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Player already exists",
        )

    # TODO: send a request to table owner to approve the new player before adding them

    player = Player(user_id=user.id, table_id=table.id)
    session.add(player)

    await session.commit()
    await session.refresh(player)

    return player.id


@router.get("/{table_id}/players", description="Get all players in the target table")
async def get_table_players(
    table_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[PlayerResponse]:
    table = await _get_table_model(table_id, session)

    validate_permission(user, table)

    return [PlayerResponse.model_validate(p) for p in table.players]


@router.put("/{table_id}/players", status_code=status.HTTP_204_NO_CONTENT)
async def leave_table(
    table_id: uuid.UUID,
    cash_out: int = Query(ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    table = await _get_table_model(table_id, session)

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    result = await session.execute(
        select(Player).where(Player.user_id == user.id, Player.table_id == table_id)
    )
    player = result.scalars().first()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if not player.is_playing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Player already left"
        )

    if not (user.is_superuser or player.user_id == user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to get this player",
        )

    player.cash_out = cash_out
    player.is_playing = False

    await session.commit()


@router.put("/{table_id}/players/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_player(
    table_id: uuid.UUID,
    player_id: uuid.UUID,
    cash_out: int = Query(ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    table = await _get_table_model(table_id, session)

    if table.finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Table already finished"
        )

    player = await get_player_model(player_id, session, selectinload(Player.user))

    if not player.is_playing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Player already left"
        )

    if not user.is_superuser and table.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to get this player",
        )

    player.cash_out = cash_out
    player.is_playing = False

    await session.commit()


def get_transactions(players: Iterable[PlayerResponse]) -> list[TransactionResponse]:
    net_balances = {p.username: p.cash_out - p.buy_in for p in players}
    positives = {k: v for k, v in net_balances.items() if v > 0}
    negatives = {k: -v for k, v in net_balances.items() if v < 0}

    transactions = []
    for getter, money in positives.items():
        for giver, debt in negatives.items():
            if debt == 0:
                continue

            if money >= debt:
                transactions.append(
                    TransactionResponse(giver=giver, getter=getter, money=debt)
                )
                negatives[giver] = 0
                money -= debt
            elif 0 < money < debt:
                transactions.append(
                    TransactionResponse(giver=giver, getter=getter, money=money)
                )
                negatives[giver] = debt - money
                money = 0

            if money == 0:
                break

    return transactions


@router.get("/{table_id}/results")
async def get_table_results(
    table_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResultResponse:
    table = await _get_table_model(table_id, session)

    validate_permission(user, table)

    table_response = TableResponse.model_validate(table)
    transactions = get_transactions(
        PlayerResponse.model_validate(p) for p in table.players
    )

    return ResultResponse(table=table_response, transactions=transactions)
