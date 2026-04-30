import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from ..db import get_async_session
from ..models import Club, ClubMember, GameTable, User
from ..schemas import ClubResponse, TableResponse, UserRead
from .auth import current_active_user
from .tables import join_table

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def open_club(
    name: str = Body(max_length=256, min_length=4),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> uuid.UUID:
    # Check club does not exist
    existing = await session.scalar(
        select(Club).where(
            Club.name == name,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{name} already exists",
        )

    club = Club(owner_id=user.id, name=name)
    session.add(club)

    await session.commit()
    await session.refresh(club)

    # Join immediately
    await join_club(str(club.id))

    return club.id


@router.get("/")
async def get_clubs(
    session: AsyncSession = Depends(get_async_session),
) -> list[ClubResponse]:
    result = await session.execute(select(Club).order_by(Club.opened_at.desc()))
    clubs: list[Club] = [row[0] for row in result.all()]

    return [ClubResponse.model_validate(c) for c in clubs]


async def get_club_model(
    club_id: str,
    session: AsyncSession,
    *options: Any,
) -> Club:
    club_uuid = uuid.UUID(club_id)

    stmt = select(Club).where(Club.id == club_uuid)

    if options:
        stmt = stmt.options(*options)

    result = await session.execute(stmt)
    club = result.scalars().first()

    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found",
        )

    return club


async def get_member_model(
    club_id: str,
    user_id: str,
    session: AsyncSession,
) -> ClubMember:
    club_uuid = uuid.UUID(club_id)
    user_uuid = uuid.UUID(user_id)

    result = await session.execute(
        select(ClubMember).where(
            ClubMember.user_id == user_uuid, ClubMember.club_id == club_uuid
        )
    )
    member = result.scalars().first()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    return member


@router.get("/{club_id}")
async def get_club(
    club_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ClubResponse:
    return ClubResponse.model_validate(await get_club_model(club_id, session))


@router.delete("/{club_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_club(
    club_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    club = await get_club_model(club_id, session)

    if not user.is_superuser and club.owner_id != user.id:  # Admin  # Club owner
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to delete this club",
        )

    await session.delete(club)
    await session.commit()


@router.post("/{club_id}/members")
async def join_club(
    club_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    club_uuid = uuid.UUID(club_id)

    # Check club exists (raise not found error if not)
    await get_club_model(club_id, session)

    # Check member does not exist
    existing = await session.scalar(
        select(ClubMember).where(
            ClubMember.user_id == user.id,
            ClubMember.club_id == club_uuid,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member already exists",
        )

    # TODO: send a request to club owner to approve the new member before adding them

    club_member = ClubMember(club_id=club_uuid, user_id=user.id)
    session.add(club_member)

    await session.commit()


@router.get("/{club_id}/members", description="Get all members of the club")
async def get_club_members(
    club_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> list[UserRead]:
    club = await get_club_model(
        club_id,
        session,
        selectinload(Club.members),
    )

    return [UserRead.model_validate(m) for m in club.members]


@router.delete("/{club_id}/members")
async def leave_club(
    club_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    # Get member
    member = await get_member_model(club_id, str(user.id), session)

    if (
        not user.is_superuser  # Admin
        and user.id != member.user_id  # The member himself
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to complete this action",
        )

    await session.delete(member)
    await session.commit()


@router.delete("/{club_id}/members/{user_id}")
async def remove_member(
    club_id: str,
    user_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    # Get member
    member = await get_member_model(club_id, user_id, session)
    club = await get_club_model(club_id, session)

    if (
        not user.is_superuser  # Admin
        and user.id != club.owner_id  # The owner of the club
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to complete this action",
        )

    await session.delete(member)
    await session.commit()


@router.post("/{club_id}/tables", status_code=status.HTTP_201_CREATED)
async def open_table(
    club_id: str,
    join_as_player: bool,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> uuid.UUID:
    table = GameTable(owner_id=user.id, club_id=uuid.UUID(club_id))
    session.add(table)

    await session.commit()
    await session.refresh(table)

    if join_as_player:
        await join_table(str(table.id), user, session)

    return table.id


@router.get("/{club_id}/tables", description="Get all tables of the club")
async def get_club_tables(
    club_id: str,
    open_tables_only: bool | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[TableResponse]:
    club = await get_club_model(
        club_id,
        session,
        selectinload(Club.members),
    )

    valid_tables = (
        [t for t in club.tables if not t.finished] if open_tables_only else club.tables
    )

    return [TableResponse.model_validate(t) for t in valid_tables]


@router.get("/{club_id}/leaderboard")
async def get_leaderboard(
    club_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, int]:
    club = await get_club_model(
        club_id, session, selectinload(Club.tables).selectinload(GameTable.players)
    )

    leaderboard: dict[str, int] = {}

    for table in club.tables:
        if not table.finished:
            continue

        for player in table.players:
            username = player.username

            if username not in leaderboard:
                leaderboard[username] = 0

            net_balance = player.cash_out - player.buy_in
            leaderboard[username] += net_balance

    return dict(sorted(leaderboard.items(), key=lambda item: item[1]))
