from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.transaction import Transaction, TransactionType


def freeze_bounty(db: Session, agent: Agent, amount: float, demand_id: str) -> None:
    if agent.balance < amount:
        raise ValueError("Insufficient balance")
    agent.balance -= amount
    agent.frozen_balance += amount
    tx = Transaction(
        type=TransactionType.BOUNTY_FREEZE.value,
        from_agent_id=agent.id,
        amount=amount,
        demand_id=demand_id,
    )
    db.add(tx)


def release_bounty(db: Session, agent: Agent, amount: float, demand_id: str) -> None:
    """Return frozen bounty to agent (demand cancelled)."""
    agent.frozen_balance -= amount
    agent.balance += amount
    tx = Transaction(
        type=TransactionType.BOUNTY_RELEASE.value,
        to_agent_id=agent.id,
        amount=amount,
        demand_id=demand_id,
    )
    db.add(tx)


def settle_bounty(db: Session, requester: Agent, executor: Agent, amount: float, demand_id: str) -> None:
    """Transfer bounty from requester's frozen balance to executor, minus platform fee."""
    fee = round(amount * settings.platform_fee_rate, 4)
    payout = round(amount - fee, 4)

    requester.frozen_balance -= amount

    executor.balance += payout
    db.add(Transaction(
        type=TransactionType.BOUNTY_EARN.value,
        from_agent_id=requester.id,
        to_agent_id=executor.id,
        amount=payout,
        demand_id=demand_id,
    ))

    if fee > 0:
        db.add(Transaction(
            type=TransactionType.PLATFORM_FEE.value,
            from_agent_id=requester.id,
            amount=fee,
            demand_id=demand_id,
        ))


def get_transactions(
    db: Session,
    agent_id: str,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Transaction], int]:
    from sqlalchemy import or_

    query = db.query(Transaction).filter(
        or_(Transaction.from_agent_id == agent_id, Transaction.to_agent_id == agent_id)
    )
    total = query.count()
    txs = query.order_by(Transaction.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return txs, total
