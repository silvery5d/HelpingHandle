from datetime import datetime

from pydantic import BaseModel, Field


class LocationSchema(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    location: LocationSchema | None = None


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
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
