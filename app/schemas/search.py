from typing import Any

from pydantic import BaseModel


class SearchFilters(BaseModel):
    capability_types: list[str] | None = None
    online_only: bool = True
    max_distance_km: float | None = None
    reference_location: dict[str, float] | None = None  # {"latitude": ..., "longitude": ...}


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters | None = None
    max_results: int = 10


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
