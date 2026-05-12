import datetime
import uuid

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Uuid,
    func,
    select,
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


def now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


# Association Tables
club_members = Table(
    "club_members",
    Base.metadata,
    Column("club_id", Uuid(as_uuid=True), ForeignKey("clubs.id"), primary_key=True),
    Column("user_id", Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True),
)


class TimeStampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=now,
    )


# Mapped Tables
class User(SQLAlchemyBaseUserTableUUID, TimeStampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, unique=True)

    tables: Mapped[list["GameTable"]] = relationship(
        "GameTable", back_populates="owner", cascade="all, delete-orphan"
    )
    players: Mapped[list["Player"]] = relationship(
        "Player", back_populates="user", cascade="all, delete-orphan"
    )
    clubs: Mapped[list["Club"]] = relationship(
        "Club", back_populates="owner", cascade="all, delete-orphan"
    )

    member_of_clubs: Mapped[list["Club"]] = relationship(
        "Club",
        secondary=club_members,
        back_populates="members",
    )


class BuyInTransaction(TimeStampMixin, Base):
    __tablename__ = "buy_ins"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id")
    )
    amount: Mapped[int] = mapped_column(Integer)

    player: Mapped["Player"] = relationship(
        "Player", back_populates="buy_ins", foreign_keys=[player_id]
    )


class Player(TimeStampMixin, Base):
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
    cash_out: Mapped[int] = mapped_column(Integer, default=0)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=True)

    table: Mapped["GameTable"] = relationship(
        "GameTable", back_populates="players", foreign_keys=[table_id]
    )
    user: Mapped[User] = relationship(
        User, back_populates="players", foreign_keys=[user_id]
    )
    buy_ins: Mapped[list[BuyInTransaction]] = relationship(
        BuyInTransaction, back_populates="player", cascade="all, delete-orphan"
    )

    buy_in: Mapped[int] = column_property(
        select(func.coalesce(func.sum(BuyInTransaction.amount), 0))
        .where(BuyInTransaction.player_id == id)
        .correlate_except(BuyInTransaction)
        .scalar_subquery()
    )
    username: Mapped[str] = column_property(
        select(User.username)
        .where(User.id == user_id)
        .correlate_except(User)
        .scalar_subquery()
    )


class GameTable(TimeStampMixin, Base):
    __tablename__ = "game_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clubs.id"),
    )
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=None
    )

    bank: Mapped[int] = column_property(
        select(func.coalesce(func.sum(Player.buy_in), 0))
        .where(Player.table_id == id)
        .correlate_except(Player)
        .scalar_subquery()
    )

    owner: Mapped[User] = relationship(
        User, back_populates="tables", foreign_keys=[owner_id]
    )
    players: Mapped[list[Player]] = relationship(
        Player, back_populates="table", cascade="all, delete-orphan"
    )
    club: Mapped["Club"] = relationship(
        "Club", foreign_keys=[club_id], back_populates="tables"
    )

    def close_table(self):
        self.finished = True
        self.finished_at = now()


class Club(TimeStampMixin, Base):
    __tablename__ = "clubs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    # Owner (one-to-many)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
    )

    owner: Mapped[User] = relationship(
        User,
        back_populates="clubs",
        foreign_keys=[owner_id],
    )
    # Members (many-to-many)
    members: Mapped[list[User]] = relationship(
        "User",
        secondary=club_members,
        back_populates="member_of_clubs",
    )
    tables: Mapped[list[GameTable]] = relationship(
        "GameTable", back_populates="club", cascade="all, delete-orphan"
    )
