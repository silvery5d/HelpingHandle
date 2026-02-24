from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.capability import CapabilityStatus, CapabilityType


class CapabilityCreate(BaseModel):
    type: CapabilityType
    description: str
    device_info: str | None = None
    metadata: dict[str, Any] | None = None


class CapabilityUpdate(BaseModel):
    description: str | None = None
    device_info: str | None = None
    status: CapabilityStatus | None = None
    metadata: dict[str, Any] | None = None


class CapabilityResponse(BaseModel):
    id: str
    agent_id: str
    type: str
    description: str
    device_info: str | None
    status: str
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CapabilityListResponse(BaseModel):
    capabilities: list[CapabilityResponse]
    total: int
    page: int
    per_page: int
