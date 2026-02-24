from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LocationPreference(BaseModel):
    latitude: float
    longitude: float
    radius_km: float


class DemandCreate(BaseModel):
    description: str
    requirements: dict[str, Any] | None = None
    location_preference: LocationPreference | None = None
    bounty_amount: float = 0.0


class DemandResponse(BaseModel):
    id: str
    requester_agent_id: str
    description: str
    requirements: dict[str, Any] | None
    location_latitude: float | None
    location_longitude: float | None
    location_radius_km: float | None
    bounty_amount: float
    status: str
    accepted_agent_id: str | None
    matched_results: Any | None
    verification_id: str | None = None
    verification_votes: int | None = None
    verification_required: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DemandListResponse(BaseModel):
    demands: list[DemandResponse]
    total: int
    page: int
    per_page: int


class AcceptRequest(BaseModel):
    agent_id: str
