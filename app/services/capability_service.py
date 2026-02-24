from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.capability import Capability
from app.schemas.capability import CapabilityCreate, CapabilityUpdate


def create_capability(db: Session, agent_id: str, data: CapabilityCreate) -> Capability:
    cap = Capability(
        agent_id=agent_id,
        type=data.type.value,
        description=data.description,
        device_info=data.device_info,
        metadata_json=data.metadata,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)
    return cap


def get_capability(db: Session, capability_id: str) -> Capability | None:
    return db.query(Capability).filter(Capability.id == capability_id).first()


def update_capability(db: Session, cap: Capability, data: CapabilityUpdate) -> Capability:
    if data.description is not None:
        cap.description = data.description
    if data.device_info is not None:
        cap.device_info = data.device_info
    if data.status is not None:
        cap.status = data.status.value
    if data.metadata is not None:
        cap.metadata_json = data.metadata
    cap.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cap)
    return cap


def delete_capability(db: Session, cap: Capability) -> None:
    db.delete(cap)
    db.commit()


def list_capabilities(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    cap_type: str | None = None,
    status: str | None = None,
    agent_id: str | None = None,
) -> tuple[list[Capability], int]:
    query = db.query(Capability)
    if cap_type:
        query = query.filter(Capability.type == cap_type)
    if status:
        query = query.filter(Capability.status == status)
    if agent_id:
        query = query.filter(Capability.agent_id == agent_id)
    total = query.count()
    caps = query.order_by(Capability.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return caps, total
