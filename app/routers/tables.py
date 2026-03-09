import datetime
import uuid
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from ..db import get_async_session
from ..models import GameTable, Player, User
from ..schemas import (
    PlayerResponse,
    ResultResponse,
    TableResponse,
    TransactionResponse,
)
from .auth import current_active_user

router = APIRouter(prefix="/tables", tags=["tables"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def open_table(
    join_as_player: bool,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> uuid.UUID:
    table = GameTable(user_id=user.id)
    session.add(table)

    await session.commit()
    await session.refresh(table)

    if join_as_player:
        from .players import join_table

        await join_table(str(table.id), user, session)

    return table.id


@router.get("/")
async def get_tables(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[TableResponse]:
    result = await session.execute(
        select(GameTable)
        .filter_by(user_id=user.id)
        .order_by(GameTable.started_at.desc())
    )
    tables: list[GameTable] = [row[0] for row in result.all()]

    return [
        TableResponse(
            id=t.id,
            user_id=t.user_id,
            bank=t.bank,
            finished=t.finished,
            started_at=t.started_at,
            finished_at=t.finished_at,
        )
        for t in tables
    ]


async def get_table_model(table_id: str, session: AsyncSession) -> GameTable:
    table_uuid = uuid.UUID(table_id)

    result = await session.execute(
        select(GameTable)
        .where(GameTable.id == table_uuid)
        .options(selectinload(GameTable.players).selectinload(Player.user))
    )
    table = result.scalars().first()

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Table not found"
        )

    return table


@router.get("/{table_id}")
async def get_table(
    table_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> TableResponse:
    table = await get_table_model(table_id, session)

    return TableResponse(
        id=table.id,
        user_id=table.user_id,
        bank=table.bank,
        finished=table.finished,
        started_at=table.started_at,
        finished_at=table.finished_at,
    )


@router.get("/{table_id}/players", description="Get all players in the target table")
async def get_table_players(
    table_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> list[PlayerResponse]:
    table = await get_table_model(table_id, session)
    players = table.players

    return [
        PlayerResponse(
            id=p.id,
            table_id=table.id,
            username=p.user.username,
            cash_in=p.cash_in,
            cash_out=p.cash_out,
        )
        for p in players
    ]


def get_transactions(players: Iterable[PlayerResponse]) -> list[TransactionResponse]:
    net_balances = {p.username: p.cash_out - p.cash_in for p in players}
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


@router.get("/{table_id}/result")
async def get_table_result(
    table_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ResultResponse:
    table = await get_table_model(table_id, session)
    players = table.players

    table_response = TableResponse(
        id=table.id,
        user_id=table.user_id,
        bank=table.bank,
        finished=table.finished,
        started_at=table.started_at,
        finished_at=table.finished_at,
    )

    transactions = get_transactions(
        PlayerResponse(
            id=p.id,
            table_id=table.id,
            username=p.user.username,
            cash_in=p.cash_in,
            cash_out=p.cash_out,
        )
        for p in players
    )

    return ResultResponse(table=table_response, transactions=transactions)


@router.put("/{table_id}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_table(
    table_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    table = await get_table_model(table_id, session)

    if not user.is_superuser and table.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to close this table",
        )

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
                detail=f"Player with username {p.user.username} must first leave the table",
            )

    await session.commit()


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    table = await get_table_model(table_id, session)

    if not user.is_superuser and table.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to delete this table",
        )

    await session.delete(table)
    await session.commit()
