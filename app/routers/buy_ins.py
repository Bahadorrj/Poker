import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from ..db import get_async_session
from ..models import BuyInTransaction, Club, GameTable, Player, User
from ..schemas import BuyInResponse, BuyInUpdate
from .auth import current_active_user
from .tables import member_permission, super_permission

router = APIRouter(prefix="/buy-ins", tags=["buy-ins"])


async def get_buy_in_model(
    transaction_id: uuid.UUID,
    session: AsyncSession,
    *options: Any,
) -> BuyInTransaction:
    stmt = select(BuyInTransaction).where(BuyInTransaction.id == transaction_id)

    if options:
        stmt = stmt.options(*options)

    result = await session.execute(stmt)
    transaction = result.scalars().first()

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    return transaction


async def _get_buy_in_model(
    transaction_id: uuid.UUID,
    permission: Callable,
    user: User,
    session: AsyncSession,
) -> BuyInTransaction:
    buy_in = await get_buy_in_model(
        transaction_id,
        session,
        selectinload(BuyInTransaction.player)
        .selectinload(Player.table)
        .selectinload(GameTable.club)
        .selectinload(Club.members),
    )

    if permission:
        permission(user, buy_in.player.table)

    return buy_in


@router.get("/{transaction_id}")
async def get_buy_in(
    transaction_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> BuyInResponse:
    transaction = await _get_buy_in_model(
        transaction_id, member_permission, user, session
    )

    return BuyInResponse.model_validate(transaction)


@router.patch("/{transaction_id}")
async def update_buy_in(
    transaction_id: uuid.UUID,
    buy_in_update: BuyInUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    transaction = await _get_buy_in_model(
        transaction_id, super_permission, user, session
    )

    transaction.amount = buy_in_update.amount

    await session.commit()


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_buy_in(
    transaction_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    transaction = await _get_buy_in_model(
        transaction_id, super_permission, user, session
    )

    await session.delete(transaction)
    await session.commit()
