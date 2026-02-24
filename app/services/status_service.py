from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agent_status import AgentStatus
from app.schemas.agent_status import StatusEntry


def upsert_statuses(db: Session, agent_id: str, entries: list[StatusEntry]) -> list[AgentStatus]:
    now = datetime.now(timezone.utc)
    results = []
    for entry in entries:
        existing = (
            db.query(AgentStatus)
            .filter(AgentStatus.agent_id == agent_id, AgentStatus.key == entry.key)
            .first()
        )
        if existing:
            existing.value = entry.value
            existing.updated_at = now
            results.append(existing)
        else:
            status = AgentStatus(
                agent_id=agent_id,
                key=entry.key,
                value=entry.value,
                updated_at=now,
            )
            db.add(status)
            results.append(status)
    db.commit()
    for r in results:
        db.refresh(r)
    return results


def get_agent_statuses(db: Session, agent_id: str) -> list[AgentStatus]:
    return db.query(AgentStatus).filter(AgentStatus.agent_id == agent_id).all()
