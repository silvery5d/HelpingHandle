from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.limiter import limiter
from app.models.agent import Agent
from app.schemas.demand import AcceptRequest, DemandCreate, DemandListResponse, DemandResponse, ForMeResponse
from app.services.demand_service import (
    accept_demand,
    close_demand,
    complete_demand,
    create_demand,
    get_demand,
    list_demands,
    match_demand,
)
from app.services.matching_service import find_demands_for_agent

router = APIRouter(prefix="/api/demands", tags=["demands"])


def _to_response(d) -> DemandResponse:
    verification_id = None
    verification_votes = None
    verification_required = None
    if d.verification:
        verification_id = d.verification.id
        verification_votes = len(d.verification.votes)
        verification_required = d.verification.required_votes

    return DemandResponse(
        id=d.id,
        requester_agent_id=d.requester_agent_id,
        description=d.description,
        requirements=d.requirements_json,
        location_latitude=d.location_latitude,
        location_longitude=d.location_longitude,
        location_radius_km=d.location_radius_km,
        bounty_amount=d.bounty_amount,
        status=d.status,
        accepted_agent_id=d.accepted_agent_id,
        matched_results=d.matched_results_json,
        verification_id=verification_id,
        verification_votes=verification_votes,
        verification_required=verification_required,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.post("", response_model=DemandResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def create(request: Request, data: DemandCreate, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    try:
        demand = create_demand(db, agent, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(demand)


@router.get("", response_model=DemandListResponse)
def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    demand_status: str | None = Query(None, alias="status"),
    requester_id: str | None = None,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    demands, total = list_demands(db, page, per_page, demand_status, requester_id)
    return DemandListResponse(
        demands=[_to_response(d) for d in demands],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/for-me", response_model=ForMeResponse)
@limiter.limit("10/hour")
def demands_for_me(
    request: Request,
    max_results: int = Query(10, ge=1, le=50),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Find open demands that match the current agent's capabilities."""
    result = find_demands_for_agent(db, agent, max_results=max_results)
    return ForMeResponse(**result)


@router.get("/{demand_id}", response_model=DemandResponse)
def get_one(demand_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    demand = get_demand(db, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    return _to_response(demand)


@router.post("/{demand_id}/match")
@limiter.limit("5/hour")
def trigger_match(request: Request, demand_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    demand = get_demand(db, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    if demand.requester_agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your demand")
    result = match_demand(db, demand)
    return result


@router.post("/{demand_id}/accept", response_model=DemandResponse)
def accept(
    demand_id: str,
    data: AcceptRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    demand = get_demand(db, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    if demand.requester_agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your demand")
    try:
        demand = accept_demand(db, demand, data.agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(demand)


@router.post("/{demand_id}/complete", response_model=DemandResponse)
def complete(demand_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    demand = get_demand(db, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    if demand.requester_agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your demand")
    try:
        demand = complete_demand(db, demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(demand)


@router.post("/{demand_id}/close", response_model=DemandResponse)
def close(demand_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    demand = get_demand(db, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    if demand.requester_agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your demand")
    try:
        demand = close_demand(db, demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(demand)
