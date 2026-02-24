from typing import Any

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    capability_types: list[str] | None = None
    online_only: bool = True
    max_distance_km: float | None = Field(default=None, gt=0, le=50000)
    reference_location: dict[str, float] | None = None  # {"latitude": ..., "longitude": ...}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: SearchFilters | None = None
    max_results: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    agent_id: str
    agent_name: str
    capability_id: str
    capability_type: str
    capability_description: str
    relevance_score: float
    distance_km: float | None
    reasoning: str
    agent_statuses: dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    interpreted_query: dict[str, Any]
    results: list[SearchResultItem]
    total_results: int
    matching_method: str
