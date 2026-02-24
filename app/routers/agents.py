from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.limiter import ip_limiter, limiter
from app.models.agent import Agent
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentPublic,
    AgentRegistered,
    AgentResponse,
    AgentUpdate,
    LocationSchema,
)
from app.services.agent_service import get_agent_by_id, list_agents, register_agent, update_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _to_location(agent: Agent) -> LocationSchema | None:
    if agent.latitude is not None and agent.longitude is not None:
        return LocationSchema(latitude=agent.latitude, longitude=agent.longitude)
    return None


@router.post("/register", response_model=AgentRegistered, status_code=status.HTTP_201_CREATED)
@ip_limiter.limit("5/hour")
def register(request: Request, data: AgentCreate, db: Session = Depends(get_db)):
    agent, raw_key = register_agent(db, data)
    return AgentRegistered(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        location=_to_location(agent),
        balance=agent.balance,
        frozen_balance=agent.frozen_balance,
        created_at=agent.created_at,
        last_seen=agent.last_seen,
        api_key=raw_key,
    )


@router.get("/me", response_model=AgentResponse)
def get_me(agent: Agent = Depends(get_current_agent)):
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        location=_to_location(agent),
        balance=agent.balance,
        frozen_balance=agent.frozen_balance,
        created_at=agent.created_at,
        last_seen=agent.last_seen,
    )


@router.patch("/me", response_model=AgentResponse)
@limiter.limit("30/hour")
def update_me(request: Request, data: AgentUpdate, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    agent = update_agent(db, agent, data)
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        location=_to_location(agent),
        balance=agent.balance,
        frozen_balance=agent.frozen_balance,
        created_at=agent.created_at,
        last_seen=agent.last_seen,
    )


@router.post("/heartbeat")
def heartbeat(agent: Agent = Depends(get_current_agent)):
    return {"status": "ok", "last_seen": agent.last_seen}


@router.get("", response_model=AgentListResponse)
def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    agents, total = list_agents(db, page, per_page)
    return AgentListResponse(
        agents=[
            AgentPublic(
                id=a.id,
                name=a.name,
                description=a.description,
                location=_to_location(a),
                last_seen=a.last_seen,
                capabilities_count=len(a.capabilities),
            )
            for a in agents
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{agent_id}", response_model=AgentPublic)
def get_agent(agent_id: str, agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = get_agent_by_id(db, agent_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentPublic(
        id=target.id,
        name=target.name,
        description=target.description,
        location=_to_location(target),
        last_seen=target.last_seen,
        capabilities_count=len(target.capabilities),
    )
