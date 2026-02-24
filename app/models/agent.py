import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    api_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    balance = Column(Float, nullable=False, default=0.0)
    frozen_balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    capabilities = relationship("Capability", back_populates="agent", cascade="all, delete-orphan")
    statuses = relationship("AgentStatus", back_populates="agent", cascade="all, delete-orphan")
    demands = relationship("Demand", back_populates="requester_agent", foreign_keys="Demand.requester_agent_id", cascade="all, delete-orphan")
    accepted_demands = relationship("Demand", back_populates="accepted_agent", foreign_keys="Demand.accepted_agent_id")
