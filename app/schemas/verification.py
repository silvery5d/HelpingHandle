from datetime import datetime

from pydantic import BaseModel


class VerificationVoteResponse(BaseModel):
    id: str
    verification_id: str
    voter_agent_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VerificationResponse(BaseModel):
    id: str
    demand_id: str
    requester_agent_id: str
    executor_agent_id: str
    bounty_amount: float
    required_votes: int
    current_votes: int
    status: str
    created_at: datetime
    settled_at: datetime | None
    votes: list[VerificationVoteResponse]

    model_config = {"from_attributes": True}


class VerificationListResponse(BaseModel):
    verifications: list[VerificationResponse]
    total: int
    page: int
    per_page: int
