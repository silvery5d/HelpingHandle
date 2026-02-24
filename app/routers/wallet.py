from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.api_key import get_current_agent
from app.database import get_db
from app.models.agent import Agent
from app.schemas.wallet import TransactionListResponse, TransactionResponse, WalletResponse
from app.services.wallet_service import get_transactions

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.get("", response_model=WalletResponse)
def get_wallet(agent: Agent = Depends(get_current_agent)):
    return WalletResponse(
        agent_id=agent.id,
        balance=agent.balance,
        frozen_balance=agent.frozen_balance,
        total=agent.balance + agent.frozen_balance,
    )


@router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    txs, total = get_transactions(db, agent.id, page, per_page)
    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                id=t.id,
                type=t.type,
                from_agent_id=t.from_agent_id,
                to_agent_id=t.to_agent_id,
                amount=t.amount,
                demand_id=t.demand_id,
                created_at=t.created_at,
            )
            for t in txs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )
