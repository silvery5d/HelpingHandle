import secrets

from sqlalchemy.orm import Session

from app.auth.api_key import hash_api_key
from app.config import settings
from app.models.agent import Agent
from app.models.transaction import Transaction, TransactionType
from app.schemas.agent import AgentCreate, AgentUpdate


def register_agent(db: Session, data: AgentCreate) -> tuple[Agent, str]:
    raw_key = f"{settings.api_key_prefix}{secrets.token_urlsafe(32)}"
    agent = Agent(
        name=data.name,
        description=data.description,
        api_key_hash=hash_api_key(raw_key),
        latitude=data.location.latitude if data.location else None,
        longitude=data.location.longitude if data.location else None,
        balance=settings.initial_balance,
        frozen_balance=0.0,
    )
    db.add(agent)
    db.flush()

    tx = Transaction(
        type=TransactionType.INITIAL_GRANT.value,
        to_agent_id=agent.id,
        amount=settings.initial_balance,
    )
    db.add(tx)
    db.commit()
    db.refresh(agent)
    return agent, raw_key


def update_agent(db: Session, agent: Agent, data: AgentUpdate) -> Agent:
    if data.name is not None:
        agent.name = data.name
    if data.description is not None:
        agent.description = data.description
    if data.location is not None:
        agent.latitude = data.location.latitude
        agent.longitude = data.location.longitude
    db.commit()
    db.refresh(agent)
    return agent


def get_agent_by_id(db: Session, agent_id: str) -> Agent | None:
    return db.query(Agent).filter(Agent.id == agent_id).first()


def list_agents(db: Session, page: int = 1, per_page: int = 20) -> tuple[list[Agent], int]:
    query = db.query(Agent)
    total = query.count()
    agents = query.order_by(Agent.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return agents, total
