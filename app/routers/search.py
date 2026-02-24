from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.models.agent import Agent
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.matching_service import semantic_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/capabilities", response_model=SearchResponse)
def search_capabilities(
    data: SearchRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    ref_lat = None
    ref_lon = None
    max_dist = None
    cap_types = None
    online_only = True

    if data.filters:
        cap_types = data.filters.capability_types
        online_only = data.filters.online_only
        max_dist = data.filters.max_distance_km
        if data.filters.reference_location:
            ref_lat = data.filters.reference_location.get("latitude")
            ref_lon = data.filters.reference_location.get("longitude")

    result = semantic_search(
        db=db,
        query=data.query,
        capability_types=cap_types,
        online_only=online_only,
        ref_lat=ref_lat,
        ref_lon=ref_lon,
        max_distance_km=max_dist,
        max_results=data.max_results,
    )

    return SearchResponse(
        query=result.get("query", data.query),
        interpreted_query=result.get("interpreted_query", {}),
        results=[SearchResultItem(**r) for r in result.get("results", [])],
        total_results=result.get("total_results", 0),
        matching_method=result.get("matching_method", "none"),
    )
