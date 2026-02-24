from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.demand import Demand, DemandStatus
from app.schemas.demand import DemandCreate
from app.services.matching_service import semantic_search
from app.services.verification_service import cancel_verification, create_verification, get_verification_by_demand
from app.services.wallet_service import freeze_bounty, release_bounty


def create_demand(db: Session, agent: Agent, data: DemandCreate) -> Demand:
    demand = Demand(
        requester_agent_id=agent.id,
        description=data.description,
        requirements_json=data.requirements,
        location_latitude=data.location_preference.latitude if data.location_preference else None,
        location_longitude=data.location_preference.longitude if data.location_preference else None,
        location_radius_km=data.location_preference.radius_km if data.location_preference else None,
        bounty_amount=data.bounty_amount,
    )
    db.add(demand)
    db.flush()

    if data.bounty_amount > 0:
        freeze_bounty(db, agent, data.bounty_amount, demand.id)

    db.commit()
    db.refresh(demand)
    return demand


def get_demand(db: Session, demand_id: str) -> Demand | None:
    return db.query(Demand).filter(Demand.id == demand_id).first()


def list_demands(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    requester_id: str | None = None,
) -> tuple[list[Demand], int]:
    query = db.query(Demand)
    if status:
        query = query.filter(Demand.status == status)
    if requester_id:
        query = query.filter(Demand.requester_agent_id == requester_id)
    total = query.count()
    demands = query.order_by(Demand.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return demands, total


def match_demand(db: Session, demand: Demand) -> dict:
    cap_types = None
    if demand.requirements_json and "capability_types" in demand.requirements_json:
        cap_types = demand.requirements_json["capability_types"]

    result = semantic_search(
        db=db,
        query=demand.description,
        capability_types=cap_types,
        ref_lat=demand.location_latitude,
        ref_lon=demand.location_longitude,
        max_distance_km=demand.location_radius_km,
    )

    demand.matched_results_json = result.get("results", [])
    db.commit()
    return result


def accept_demand(db: Session, demand: Demand, executor_agent_id: str) -> Demand:
    if demand.status != DemandStatus.OPEN.value:
        raise ValueError(f"Demand is {demand.status}, expected open")
    executor = db.query(Agent).filter(Agent.id == executor_agent_id).first()
    if executor is None:
        raise ValueError("Executor agent not found")
    demand.status = DemandStatus.ACCEPTED.value
    demand.accepted_agent_id = executor_agent_id
    db.commit()
    db.refresh(demand)
    return demand


def complete_demand(db: Session, demand: Demand) -> Demand:
    if demand.status != DemandStatus.ACCEPTED.value:
        raise ValueError(f"Demand is {demand.status}, expected accepted")

    if demand.bounty_amount > 0:
        create_verification(db, demand)
        demand.status = DemandStatus.VERIFYING.value
    else:
        demand.status = DemandStatus.COMPLETED.value

    db.commit()
    db.refresh(demand)
    return demand


def close_demand(db: Session, demand: Demand) -> Demand:
    allowed = (DemandStatus.OPEN.value, DemandStatus.ACCEPTED.value, DemandStatus.VERIFYING.value)
    if demand.status not in allowed:
        raise ValueError(f"Demand is {demand.status}, cannot close")

    if demand.status == DemandStatus.VERIFYING.value:
        verification = get_verification_by_demand(db, demand.id)
        if verification:
            cancel_verification(db, verification)
    elif demand.bounty_amount > 0:
        requester = db.query(Agent).filter(Agent.id == demand.requester_agent_id).first()
        release_bounty(db, requester, demand.bounty_amount, demand.id)

    demand.status = DemandStatus.CLOSED.value
    db.commit()
    db.refresh(demand)
    return demand
