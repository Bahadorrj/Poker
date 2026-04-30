import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field
from fastapi_users import schemas


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
    username: str = Field(max_length=256)
    buy_in: int = Field(ge=0)
    cash_out: int = Field(ge=0)
    is_playing: bool = True


class UserHistoryResponse(PokerBaseModel):
    history: list[PlayerResponse]
    net_balance: int
    total_time: datetime.time


class TableResponse(PokerBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    bank: int = Field(ge=0)
    finished: bool
    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None


class TransactionResponse(PokerBaseModel):
    giver: str
    getter: str
    money: int = Field(gt=0)


class ResultResponse(PokerBaseModel):
    table: TableResponse
    transactions: list[TransactionResponse]
