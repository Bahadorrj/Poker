import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

load_dotenv()

from .db import create_db_and_tables, get_async_session
from .routers import auth, users, players, tables
from .models import User

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},  # don't leak exc details
    )


# Auth
app.include_router(auth.router)

# Users
app.include_router(users.router)

# Tables
app.include_router(tables.router)

# Players
app.include_router(players.router)


# Default
@app.get("/leaderboard")
async def get_leaderboard(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, int]:
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .options(selectinload(User.players))
    )
    all_users: list[User] = [row[0] for row in result.all()]

    leaderboard: dict[str, int] = {}

    for user in all_users:
        if user.username not in leaderboard:
            leaderboard[user.username] = 0

        for player in user.players:
            net_balance = player.cash_out - player.buy_in
            leaderboard[user.username] += net_balance

    return dict(sorted(leaderboard.items(), key=lambda item: item[1]))
