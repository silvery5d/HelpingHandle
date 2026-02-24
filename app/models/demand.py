import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class DemandStatus(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    CLOSED = "closed"


class Demand(Base):
    __tablename__ = "demands"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements_json = Column(JSON, nullable=True)
    location_latitude = Column(Float, nullable=True)
    location_longitude = Column(Float, nullable=True)
    location_radius_km = Column(Float, nullable=True)
    bounty_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(10), default=DemandStatus.OPEN.value, index=True)
    accepted_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    matched_results_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    requester_agent = relationship("Agent", back_populates="demands", foreign_keys=[requester_agent_id])
    accepted_agent = relationship("Agent", back_populates="accepted_demands", foreign_keys=[accepted_agent_id])
    verification = relationship("Verification", back_populates="demand", uselist=False)
