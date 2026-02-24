from datetime import datetime

from pydantic import BaseModel


class LocationSchema(BaseModel):
    latitude: float
    longitude: float


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    location: LocationSchema | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location: LocationSchema | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    location: LocationSchema | None
    balance: float
    frozen_balance: float
    created_at: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class AgentRegistered(AgentResponse):
    api_key: str


class AgentPublic(BaseModel):
    id: str
    name: str
    description: str | None
    location: LocationSchema | None
    last_seen: datetime
    capabilities_count: int = 0

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    agents: list[AgentPublic]
    total: int
    page: int
    per_page: int
