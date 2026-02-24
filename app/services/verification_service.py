from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.demand import Demand, DemandStatus
from app.models.verification import Verification, VerificationStatus, VerificationVote
from app.services.wallet_service import release_bounty, settle_bounty


def create_verification(db: Session, demand: Demand) -> Verification:
    verification = Verification(
        demand_id=demand.id,
        requester_agent_id=demand.requester_agent_id,
        executor_agent_id=demand.accepted_agent_id,
        bounty_amount=demand.bounty_amount,
        required_votes=settings.required_verifiers,
    )
    db.add(verification)
    return verification


def get_verification(db: Session, verification_id: str) -> Verification | None:
    return db.query(Verification).filter(Verification.id == verification_id).first()


def get_verification_by_demand(db: Session, demand_id: str) -> Verification | None:
    return db.query(Verification).filter(Verification.demand_id == demand_id).first()


def list_pending_verifications(
    db: Session,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Verification], int]:
    query = db.query(Verification).filter(
        Verification.status == VerificationStatus.PENDING.value
    )
    total = query.count()
    verifications = (
        query.order_by(Verification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return verifications, total


def cast_vote(db: Session, verification: Verification, voter: Agent) -> VerificationVote:
    if verification.status != VerificationStatus.PENDING.value:
        raise ValueError(f"Verification is {verification.status}, cannot vote")
    if voter.id == verification.requester_agent_id:
        raise ValueError("Requester cannot verify their own demand")
    if voter.id == verification.executor_agent_id:
        raise ValueError("Executor cannot verify their own demand")

    existing = (
        db.query(VerificationVote)
        .filter(
            VerificationVote.verification_id == verification.id,
            VerificationVote.voter_agent_id == voter.id,
        )
        .first()
    )
    if existing:
        raise ValueError("You have already voted on this verification")

    vote = VerificationVote(
        verification_id=verification.id,
        voter_agent_id=voter.id,
    )
    db.add(vote)
    db.flush()

    vote_count = (
        db.query(VerificationVote)
        .filter(VerificationVote.verification_id == verification.id)
        .count()
    )

    if vote_count >= verification.required_votes:
        _settle_verification(db, verification)

    return vote


def _settle_verification(db: Session, verification: Verification) -> None:
    requester = db.query(Agent).filter(Agent.id == verification.requester_agent_id).first()
    executor = db.query(Agent).filter(Agent.id == verification.executor_agent_id).first()

    if verification.bounty_amount > 0:
        settle_bounty(db, requester, executor, verification.bounty_amount, verification.demand_id)

    verification.status = VerificationStatus.APPROVED.value
    verification.settled_at = datetime.now(timezone.utc)

    demand = db.query(Demand).filter(Demand.id == verification.demand_id).first()
    demand.status = DemandStatus.COMPLETED.value


def cancel_verification(db: Session, verification: Verification) -> None:
    if verification.status != VerificationStatus.PENDING.value:
        raise ValueError(f"Verification is {verification.status}, cannot cancel")
    verification.status = VerificationStatus.CANCELLED.value

    if verification.bounty_amount > 0:
        requester = db.query(Agent).filter(Agent.id == verification.requester_agent_id).first()
        release_bounty(db, requester, verification.bounty_amount, verification.demand_id)
