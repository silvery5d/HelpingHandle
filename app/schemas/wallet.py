from datetime import datetime

from pydantic import BaseModel


class WalletResponse(BaseModel):
    agent_id: str
    balance: float
    frozen_balance: float
    total: float


class TransactionResponse(BaseModel):
    id: str
    type: str
    from_agent_id: str | None
    to_agent_id: str | None
    amount: float
    demand_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    per_page: int
