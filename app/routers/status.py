from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent_status import AgentStatusListResponse, StatusBatchUpdate, StatusResponse
from app.services.agent_service import get_agent_by_id
from app.services.status_service import get_agent_statuses, upsert_statuses

router = APIRouter(prefix="/api/status", tags=["status"])


@router.put("", response_model=AgentStatusListResponse)
def update_statuses(
    data: StatusBatchUpdate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    results = upsert_statuses(db, agent.id, data.statuses)
    return AgentStatusListResponse(
        agent_id=agent.id,
        statuses=[StatusResponse(key=s.key, value=s.value, updated_at=s.updated_at) for s in results],
    )


@router.get("", response_model=AgentStatusListResponse)
def get_my_statuses(agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    statuses = get_agent_statuses(db, agent.id)
    return AgentStatusListResponse(
        agent_id=agent.id,
        statuses=[StatusResponse(key=s.key, value=s.value, updated_at=s.updated_at) for s in statuses],
    )


@router.get("/{agent_id}", response_model=AgentStatusListResponse)
def get_agent_statuses_public(
    agent_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    target = get_agent_by_id(db, agent_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    statuses = get_agent_statuses(db, agent_id)
    return AgentStatusListResponse(
        agent_id=agent_id,
        statuses=[StatusResponse(key=s.key, value=s.value, updated_at=s.updated_at) for s in statuses],
    )
