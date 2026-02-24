import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    demand_id = Column(
        String(36),
        ForeignKey("demands.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    requester_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    executor_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    bounty_amount = Column(Float, nullable=False)
    required_votes = Column(Integer, nullable=False, default=5)
    status = Column(String(10), default=VerificationStatus.PENDING.value, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    settled_at = Column(DateTime, nullable=True)

    demand = relationship("Demand", back_populates="verification")
    votes = relationship(
        "VerificationVote",
        back_populates="verification",
        cascade="all, delete-orphan",
    )


class VerificationVote(Base):
    __tablename__ = "verification_votes"
    __table_args__ = (
        UniqueConstraint("verification_id", "voter_agent_id", name="uq_verification_voter"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    verification_id = Column(
        String(36),
        ForeignKey("verifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voter_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    verification = relationship("Verification", back_populates="votes")
    voter = relationship("Agent")
