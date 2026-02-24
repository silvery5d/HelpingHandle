from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StatusEntry(BaseModel):
    key: str
    value: Any


class StatusBatchUpdate(BaseModel):
    statuses: list[StatusEntry]


class StatusResponse(BaseModel):
    key: str
    value: Any
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentStatusListResponse(BaseModel):
    agent_id: str
    statuses: list[StatusResponse]
