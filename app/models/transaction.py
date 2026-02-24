import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String

from app.database import Base


class TransactionType(str, enum.Enum):
    INITIAL_GRANT = "initial_grant"
    BOUNTY_FREEZE = "bounty_freeze"
    BOUNTY_RELEASE = "bounty_release"
    BOUNTY_EARN = "bounty_earn"
    PLATFORM_FEE = "platform_fee"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(20), nullable=False, index=True)
    from_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    to_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    amount = Column(Float, nullable=False)
    demand_id = Column(String(36), ForeignKey("demands.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
