from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.agent_status import AgentStatus
from app.models.capability import Capability, CapabilityStatus
from app.models.demand import Demand, DemandStatus
from app.models.transaction import Transaction, TransactionType

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

router = APIRouter(tags=["web"])

_skill_md_path = Path(__file__).parent.parent / "static" / "skill.md"


@router.get("/skill.md", response_class=PlainTextResponse)
def skill_md():
    return PlainTextResponse(_skill_md_path.read_text(encoding="utf-8"), media_type="text/markdown")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    online_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.agent_online_threshold_minutes)

    stats = {
        "agents_total": db.query(Agent).count(),
        "agents_online": db.query(Agent).filter(Agent.last_seen >= online_threshold).count(),
        "capabilities_total": db.query(Capability).count(),
        "capabilities_online": db.query(Capability).filter(Capability.status == CapabilityStatus.ONLINE.value).count(),
        "demands_open": db.query(Demand).filter(Demand.status == DemandStatus.OPEN.value).count(),
        "demands_total": db.query(Demand).count(),
        "demands_completed": db.query(Demand).filter(Demand.status == DemandStatus.COMPLETED.value).count(),
    }

    recent_agents = db.query(Agent).order_by(Agent.created_at.desc()).limit(10).all()
    recent_demands = db.query(Demand).order_by(Demand.created_at.desc()).limit(10).all()

    # --- Demo showcase data ---
    s1_provider = db.query(Agent).filter(Agent.id == "demo-s1-agent-video-provider").first()
    s1_consumer = db.query(Agent).filter(Agent.id == "demo-s1-agent-video-consumer").first()
    s1_demand = db.query(Demand).filter(Demand.id == "demo-s1-demand-video").first()
    s1_caps = (
        db.query(Capability).filter(Capability.agent_id == "demo-s1-agent-video-provider").all()
        if s1_provider else []
    )

    s2_drone = db.query(Agent).filter(Agent.id == "demo-s2-agent-drone").first()
    s2_architect = db.query(Agent).filter(Agent.id == "demo-s2-agent-architect").first()
    s2_demand = db.query(Demand).filter(Demand.id == "demo-s2-demand-3dmodel").first()
    s2_caps = (
        db.query(Capability).filter(Capability.agent_id == "demo-s2-agent-drone").all()
        if s2_drone else []
    )

    has_demo = s1_provider is not None and s2_drone is not None

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_agents": recent_agents,
        "recent_demands": recent_demands,
        "has_demo": has_demo,
        "s1_provider": s1_provider,
        "s1_consumer": s1_consumer,
        "s1_demand": s1_demand,
        "s1_caps": s1_caps,
        "s2_drone": s2_drone,
        "s2_architect": s2_architect,
        "s2_demand": s2_demand,
        "s2_caps": s2_caps,
    })


@router.get("/web/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/web/agents", response_class=HTMLResponse)
def agents_list(request: Request, db: Session = Depends(get_db)):
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return templates.TemplateResponse("agents.html", {"request": request, "agents": agents})


@router.get("/web/agents/{agent_id}", response_class=HTMLResponse)
def agent_detail(request: Request, agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    statuses = db.query(AgentStatus).filter(AgentStatus.agent_id == agent_id).all()
    capabilities = db.query(Capability).filter(Capability.agent_id == agent_id).all()
    return templates.TemplateResponse("agent_detail.html", {
        "request": request,
        "agent": agent,
        "statuses": statuses,
        "capabilities": capabilities,
    })


@router.get("/web/capabilities", response_class=HTMLResponse)
def capabilities_list(request: Request, db: Session = Depends(get_db)):
    capabilities = db.query(Capability).order_by(Capability.created_at.desc()).all()
    return templates.TemplateResponse("capabilities.html", {"request": request, "capabilities": capabilities})


@router.get("/web/demands", response_class=HTMLResponse)
def demands_list(request: Request, db: Session = Depends(get_db)):
    demands = db.query(Demand).order_by(Demand.created_at.desc()).all()
    return templates.TemplateResponse("demands.html", {"request": request, "demands": demands})


@router.get("/web/demands/{demand_id}", response_class=HTMLResponse)
def demand_detail(request: Request, demand_id: str, db: Session = Depends(get_db)):
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")
    return templates.TemplateResponse("demand_detail.html", {"request": request, "demand": demand})
