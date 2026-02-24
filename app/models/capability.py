import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CapabilityType(str, enum.Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    COMMUNICATION = "communication"
    COMPUTATION = "computation"


class CapabilityStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class Capability(Base):
    __tablename__ = "capabilities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=False)
    device_info = Column(Text, nullable=True)
    status = Column(String(10), default=CapabilityStatus.ONLINE.value, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent", back_populates="capabilities")
