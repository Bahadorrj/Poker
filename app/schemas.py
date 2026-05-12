import datetime
import uuid

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str = Field(max_length=256)


class UserCreate(schemas.BaseUserCreate):
    username: str = Field(max_length=256)


class UserUpdate(schemas.BaseUserUpdate):
    username: str = Field(max_length=256)


class PokerBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)


class PlayerResponse(PokerBaseModel):
    id: uuid.UUID
    table_id: uuid.UUID
    user_id: uuid.UUID
    username: str = Field(max_length=256)
    buy_in: int = Field(ge=0)
    cash_out: int = Field(ge=0)
    is_playing: bool = True


class PlayerUpdate(PokerBaseModel):
    cash_out: int = Field(ge=0)


class PayloadRequest(PokerBaseModel):
    amount: int = Field(ge=0)


class BuyInResponse(PokerBaseModel):
    id: uuid.UUID
    amount: int = Field(ge=0)


class BuyInUpdate(PokerBaseModel):
    amount: int = Field(ge=0)


class ClubRequest(PokerBaseModel):
    name: str = Field(max_length=256, min_length=4)


class ClubResponse(PokerBaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    created_at: datetime.datetime


class UserHistoryResponse(PokerBaseModel):
    history: list[PlayerResponse]
    net_balance: int
    total_time: datetime.time


class TableResponse(PokerBaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    bank: int = Field(ge=0)
    finished: bool
    created_at: datetime.datetime
    finished_at: datetime.datetime | None = None


class TransactionResponse(PokerBaseModel):
    giver: str
    getter: str
    money: int = Field(gt=0)


class ResultResponse(PokerBaseModel):
    table: TableResponse
    transactions: list[TransactionResponse]
