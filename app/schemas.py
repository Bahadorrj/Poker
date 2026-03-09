import datetime
import uuid

from pydantic import BaseModel, Field
from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str = Field(max_length=256)


class UserCreate(schemas.BaseUserCreate):
    username: str = Field(max_length=256)


class UserUpdate(schemas.BaseUserUpdate):
    username: str = Field(max_length=256)


class PlayerResponse(BaseModel):
    id: uuid.UUID
    table_id: uuid.UUID
    username: str = Field(max_length=256)
    cash_in: int = Field(ge=0)
    cash_out: int = Field(ge=0)


class UserHistoryResponse(BaseModel):
    history: list[PlayerResponse]
    net_balance: int
    total_time: datetime.time


class TableResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    bank: int = Field(ge=0)
    finished: bool
    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None


class TransactionResponse(BaseModel):
    giver: str
    getter: str
    money: int = Field(gt=0)


class ResultResponse(BaseModel):
    table: TableResponse
    transactions: list[TransactionResponse]
