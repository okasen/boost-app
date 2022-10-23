from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        if ObjectId.is_valid(v):
            return str(v)
        raise ValueError("Not a valid ObjectId")

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class WalletType(Enum):
    DONATABLE_FUNDS = "donatable_funds"
    LOAN_BALANCE = "loan_balance"

    def __str__(self) -> str:
        return self.value


class BalanceAction(Enum):
    INCREASE = "increase"
    DECREASE = "decrease"

    def __str__(self) -> str:
        return self.value


class TransferStatus(Enum):
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"

    def __str__(self) -> str:
        return self.value


class AdjustRequest(BaseModel):
    action: BalanceAction
    amount: float


class Loan(BaseModel):
    ...


class Donation(BaseModel):
    ...


class NewWalletRequest(BaseModel):
    user_id: PyObjectId = Field(default_factory=PyObjectId)
    type: WalletType


class Wallet(BaseModel):
    user_id: PyObjectId
    id: Optional[PyObjectId]
    type: WalletType
    total_balance: float = 0  # can be positive or negative, a summary of donations - loan amounts
    created: Optional[str] = datetime.now(tz=timezone.utc).timestamp()  # a timestamp
    last_updated: Optional[str] = datetime.now(tz=timezone.utc).timestamp()  # a timestamp

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class DonatableWallet(Wallet):
    donations_given: List[Optional[Donation]]


class LoanWallet(Wallet):
    loans: List[Optional[Loan]]
    donations: List[Optional[Donation]]


class TransferRequest(BaseModel):
    id: Optional[PyObjectId]
    initiator_user: PyObjectId
    source_wallet_id: PyObjectId
    target_wallet_id: PyObjectId
    amount: float
    submitted: Optional[str] = datetime.now(tz=timezone.utc).timestamp()  # a timestamp
    status: Optional[TransferStatus]
    last_updated: Optional[str] = datetime.now(tz=timezone.utc).timestamp()  # a timestamp


class TransferUpdateRequest(BaseModel):
    transfer_id: PyObjectId
    admin_id: PyObjectId
    requested_status: TransferStatus


class TransferAdminRequest(BaseModel):
    new_status: TransferStatus


class TransferResponse(BaseModel):
    transfer_id: Optional[PyObjectId]
    current_status: TransferStatus
    original_request: TransferRequest
    message: Optional[str]
    last_updated: Optional[str] = datetime.now(tz=timezone.utc).timestamp()  # a timestamp
