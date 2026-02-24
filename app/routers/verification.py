from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.models.agent import Agent
from app.schemas.verification import (
    VerificationListResponse,
    VerificationResponse,
    VerificationVoteResponse,
)
from app.services.verification_service import (
    cast_vote,
    get_verification,
    get_verification_by_demand,
    list_pending_verifications,
)

router = APIRouter(prefix="/api/verifications", tags=["verifications"])


def _to_response(v) -> VerificationResponse:
    return VerificationResponse(
        id=v.id,
        demand_id=v.demand_id,
        requester_agent_id=v.requester_agent_id,
        executor_agent_id=v.executor_agent_id,
        bounty_amount=v.bounty_amount,
        required_votes=v.required_votes,
        current_votes=len(v.votes),
        status=v.status,
        created_at=v.created_at,
        settled_at=v.settled_at,
        votes=[
            VerificationVoteResponse(
                id=vote.id,
                verification_id=vote.verification_id,
                voter_agent_id=vote.voter_agent_id,
                created_at=vote.created_at,
            )
            for vote in v.votes
        ],
    )


@router.get("", response_model=VerificationListResponse)
def list_pending(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    verifications, total = list_pending_verifications(db, page, per_page)
    return VerificationListResponse(
        verifications=[_to_response(v) for v in verifications],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/demand/{demand_id}", response_model=VerificationResponse)
def get_by_demand(
    demand_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    verification = get_verification_by_demand(db, demand_id)
    if verification is None:
        raise HTTPException(status_code=404, detail="No verification found for this demand")
    return _to_response(verification)


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_one(
    verification_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    verification = get_verification(db, verification_id)
    if verification is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    return _to_response(verification)


@router.post("/{verification_id}/vote", response_model=VerificationVoteResponse, status_code=status.HTTP_201_CREATED)
def vote(
    verification_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    verification = get_verification(db, verification_id)
    if verification is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    try:
        v = cast_vote(db, verification, agent)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return VerificationVoteResponse(
        id=v.id,
        verification_id=v.verification_id,
        voter_agent_id=v.voter_agent_id,
        created_at=v.created_at,
    )
