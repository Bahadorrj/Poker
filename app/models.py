import datetime
import uuid

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Integer,
    Boolean,
    func,
    select,
    Uuid,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    column_property,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.now,
    )

    tables: Mapped[list["GameTable"]] = relationship(
        "GameTable", back_populates="user", cascade="all, delete-orphan"
    )
    players: Mapped[list["Player"]] = relationship(
        "Player", back_populates="user", cascade="all, delete-orphan"
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id")
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("game_tables.id")
    )
    buy_in: Mapped[int] = mapped_column(Integer, default=0)
    cash_out: Mapped[int] = mapped_column(Integer, default=0)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=True)

    table: Mapped["GameTable"] = relationship(
        "GameTable", back_populates="players", foreign_keys=[table_id]
    )
    user: Mapped[User] = relationship(
        User, back_populates="players", foreign_keys=[user_id]
    )


class GameTable(Base):
    __tablename__ = "game_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
    )
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=None
    )

    bank: Mapped[int] = column_property(
        select(func.coalesce(func.sum(Player.buy_in), 0))
        .where(Player.table_id == id)
        .correlate_except(Player)
        .scalar_subquery()
    )

    user: Mapped[User] = relationship(
        User, back_populates="tables", foreign_keys=[user_id]
    )
    players: Mapped[list[Player]] = relationship(Player, back_populates="table")
