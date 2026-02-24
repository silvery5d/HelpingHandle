from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.limiter import limiter
from app.models.agent import Agent
from app.schemas.capability import (
    CapabilityCreate,
    CapabilityListResponse,
    CapabilityResponse,
    CapabilityUpdate,
)
from app.services.capability_service import (
    create_capability,
    delete_capability,
    get_capability,
    list_capabilities,
    update_capability,
)

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


def _to_response(cap) -> CapabilityResponse:
    return CapabilityResponse(
        id=cap.id,
        agent_id=cap.agent_id,
        type=cap.type,
        description=cap.description,
        device_info=cap.device_info,
        status=cap.status,
        metadata=cap.metadata_json,
        created_at=cap.created_at,
        updated_at=cap.updated_at,
    )


@router.post("", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def create(request: Request, data: CapabilityCreate, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    cap = create_capability(db, agent.id, data)
    return _to_response(cap)


@router.get("", response_model=CapabilityListResponse)
def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    type: str | None = None,
    status: str | None = None,
    agent_id: str | None = None,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    caps, total = list_capabilities(db, page, per_page, type, status, agent_id)
    return CapabilityListResponse(
        capabilities=[_to_response(c) for c in caps],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{capability_id}", response_model=CapabilityResponse)
def get_one(capability_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    cap = get_capability(db, capability_id)
    if cap is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    return _to_response(cap)


@router.patch("/{capability_id}", response_model=CapabilityResponse)
def update(
    capability_id: str,
    data: CapabilityUpdate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    cap = get_capability(db, capability_id)
    if cap is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    if cap.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your capability")
    cap = update_capability(db, cap, data)
    return _to_response(cap)


@router.delete("/{capability_id}", status_code=204)
def delete(capability_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    cap = get_capability(db, capability_id)
    if cap is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    if cap.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Not your capability")
    delete_capability(db, cap)
