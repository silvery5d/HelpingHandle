import json
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.agent_status import AgentStatus
from app.models.capability import Capability, CapabilityStatus
from app.services.geo_service import bounding_box, haversine_distance

logger = logging.getLogger(__name__)

MATCHING_SYSTEM_PROMPT = """You are a capability matching engine for HelpingHandle, an AI agent platform.
Your job is to understand what an agent needs and score how well each candidate capability matches.

You MUST respond with valid JSON only, no other text.

Response format:
{
  "interpreted_query": {
    "intent": "brief description of what the requester needs",
    "required_features": ["feature1", "feature2"],
    "location_context": "description of location relevance"
  },
  "scored_candidates": [
    {
      "capability_id": "the-uuid",
      "relevance_score": 0.95,
      "reasoning": "one sentence explaining the score"
    }
  ]
}

Scoring guidelines:
- 0.9-1.0: Near-perfect match
- 0.7-0.89: Good match, meets most requirements
- 0.5-0.69: Partial match
- 0.3-0.49: Weak match
- 0.0-0.29: Not relevant

Consider:
1. Semantic match between need and offering
2. Device/sensor type alignment
3. Agent status freshness (newer updated_at = more trustworthy)
4. Geographic proximity (distance_km provided)"""

REVERSE_MATCHING_SYSTEM_PROMPT = """You are a demand matching engine for HelpingHandle, an AI agent platform.
An agent with certain capabilities wants to find open demands it can fulfill.
Score how well the agent's capabilities match each candidate demand.

You MUST respond with valid JSON only, no other text.

Response format:
{
  "scored_demands": [
    {
      "demand_id": "the-uuid",
      "relevance_score": 0.95,
      "reasoning": "one sentence explaining why this agent can fulfill this demand"
    }
  ]
}

Scoring guidelines:
- 0.9-1.0: Agent can perfectly fulfill this demand
- 0.7-0.89: Agent can mostly fulfill it, maybe missing minor aspects
- 0.5-0.69: Partial match, agent could help but not ideal
- 0.3-0.49: Weak match
- 0.0-0.29: Agent's capabilities are not relevant to this demand

Consider:
1. Semantic alignment between the agent's capabilities and what the demand asks for
2. Whether the agent's capability types match the demand's required types
3. Geographic feasibility (if both have location data)
4. Bounty amount as a tiebreaker (higher bounty = more attractive)"""

REVERSE_MATCHING_USER_TEMPLATE = """Agent capabilities:
{capabilities_json}

Open demands to evaluate:
{demands_json}

Score how well this agent can fulfill each demand."""

MATCHING_USER_TEMPLATE = """Search query: {query}

Candidate capabilities (JSON):
{candidates_json}

Score each candidate's relevance to the search query."""


def _get_anthropic_client():
    from anthropic import Anthropic
    return Anthropic(api_key=settings.anthropic_api_key)


def prefilter_candidates(
    db: Session,
    capability_types: list[str] | None = None,
    online_only: bool = True,
    ref_lat: float | None = None,
    ref_lon: float | None = None,
    max_distance_km: float | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Stage 1: SQL-level pre-filtering. Returns candidate dicts with distance."""
    query = db.query(Capability).join(Agent, Capability.agent_id == Agent.id)

    if capability_types:
        query = query.filter(Capability.type.in_(capability_types))
    if online_only:
        query = query.filter(Capability.status == CapabilityStatus.ONLINE.value)

    if ref_lat is not None and ref_lon is not None and max_distance_km is not None:
        min_lat, max_lat, min_lon, max_lon = bounding_box(ref_lat, ref_lon, max_distance_km)
        query = query.filter(
            Agent.latitude.isnot(None),
            Agent.latitude >= min_lat,
            Agent.latitude <= max_lat,
            Agent.longitude >= min_lon,
            Agent.longitude <= max_lon,
        )

    caps = query.limit(limit or settings.max_prefilter_candidates).all()

    candidates = []
    for cap in caps:
        agent = cap.agent
        dist = None
        if ref_lat is not None and ref_lon is not None and agent.latitude is not None:
            dist = haversine_distance(ref_lat, ref_lon, agent.latitude, agent.longitude)
            if max_distance_km is not None and dist > max_distance_km:
                continue

        statuses = db.query(AgentStatus).filter(AgentStatus.agent_id == agent.id).all()
        status_dict = {
            s.key: {"value": s.value, "updated_at": s.updated_at.isoformat()}
            for s in statuses
        }

        candidates.append({
            "capability_id": cap.id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "capability_type": cap.type,
            "capability_description": cap.description,
            "device_info": cap.device_info,
            "metadata": cap.metadata_json,
            "agent_statuses": status_dict,
            "distance_km": round(dist, 2) if dist is not None else None,
        })

    return candidates


def call_claude_for_matching(query: str, candidates_json: str) -> dict:
    """Stage 2: Call Claude API for semantic scoring."""
    client = _get_anthropic_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=MATCHING_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": MATCHING_USER_TEMPLATE.format(
                query=query,
                candidates_json=candidates_json,
            ),
        }],
    )
    return json.loads(message.content[0].text)


def fallback_keyword_matching(query: str, candidates: list[dict]) -> dict:
    """Fallback: simple text similarity scoring when Claude API is unavailable."""
    query_lower = query.lower()
    scored = []
    for c in candidates:
        text = f"{c['capability_description']} {c.get('device_info', '')} {c['capability_type']}".lower()
        score = SequenceMatcher(None, query_lower, text).ratio()
        scored.append({
            "capability_id": c["capability_id"],
            "relevance_score": round(score, 3),
            "reasoning": "Keyword similarity match (fallback)",
        })
    return {
        "interpreted_query": {"intent": query, "required_features": [], "location_context": ""},
        "scored_candidates": scored,
    }


def semantic_search(
    db: Session,
    query: str,
    capability_types: list[str] | None = None,
    online_only: bool = True,
    ref_lat: float | None = None,
    ref_lon: float | None = None,
    max_distance_km: float | None = None,
    max_results: int = 10,
) -> dict:
    # Stage 1
    candidates = prefilter_candidates(
        db, capability_types, online_only, ref_lat, ref_lon, max_distance_km,
    )
    if not candidates:
        return {"interpreted_query": {}, "results": [], "total_results": 0, "matching_method": "none"}

    # Stage 2
    candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
    try:
        claude_result = call_claude_for_matching(query, candidates_json)
        method = "claude"
    except Exception as e:
        logger.warning("Claude API failed, using fallback: %s", e)
        claude_result = fallback_keyword_matching(query, candidates)
        method = "fallback_keyword"

    # Stage 3: Post-process
    scored_map = {
        s["capability_id"]: s for s in claude_result.get("scored_candidates", [])
    }

    results = []
    for c in candidates:
        score_info = scored_map.get(c["capability_id"], {})
        results.append({
            "agent_id": c["agent_id"],
            "agent_name": c["agent_name"],
            "capability_id": c["capability_id"],
            "capability_type": c["capability_type"],
            "capability_description": c["capability_description"],
            "relevance_score": score_info.get("relevance_score", 0),
            "distance_km": c["distance_km"],
            "reasoning": score_info.get("reasoning", ""),
            "agent_statuses": c["agent_statuses"],
        })

    results.sort(key=lambda r: r["relevance_score"], reverse=True)
    results = results[:max_results]

    return {
        "query": query,
        "interpreted_query": claude_result.get("interpreted_query", {}),
        "results": results,
        "total_results": len(results),
        "matching_method": method,
    }


# ── Reverse matching: find demands for an agent ──


def _build_demands_list(db: Session, agent: Agent, max_demands: int) -> list[dict]:
    """Fetch open demands (excluding those posted by the agent itself)."""
    from app.models.demand import Demand, DemandStatus
    from app.services.geo_service import haversine_distance

    demands = (
        db.query(Demand)
        .filter(Demand.status == DemandStatus.OPEN.value)
        .filter(Demand.requester_agent_id != agent.id)
        .order_by(Demand.created_at.desc())
        .limit(max_demands)
        .all()
    )

    result = []
    for d in demands:
        dist = None
        if (
            agent.latitude is not None
            and d.location_latitude is not None
        ):
            dist = haversine_distance(
                agent.latitude, agent.longitude,
                d.location_latitude, d.location_longitude,
            )
            if d.location_radius_km and dist > d.location_radius_km:
                continue  # agent is outside demand's required radius

        result.append({
            "demand_id": d.id,
            "description": d.description,
            "requirements": d.requirements_json,
            "bounty_amount": d.bounty_amount,
            "location_latitude": d.location_latitude,
            "location_longitude": d.location_longitude,
            "location_radius_km": d.location_radius_km,
            "distance_km": round(dist, 2) if dist is not None else None,
            "created_at": d.created_at.isoformat(),
        })
    return result


def _build_agent_capabilities_summary(db: Session, agent: Agent) -> list[dict]:
    """Build a summary of the agent's capabilities for the matching prompt."""
    caps = (
        db.query(Capability)
        .filter(Capability.agent_id == agent.id)
        .all()
    )
    return [
        {
            "capability_id": c.id,
            "type": c.type,
            "description": c.description,
            "device_info": c.device_info,
            "status": c.status,
        }
        for c in caps
    ]


def _call_claude_for_reverse_matching(capabilities_json: str, demands_json: str) -> dict:
    """Call Claude API to score demands against agent capabilities."""
    client = _get_anthropic_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=REVERSE_MATCHING_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": REVERSE_MATCHING_USER_TEMPLATE.format(
                capabilities_json=capabilities_json,
                demands_json=demands_json,
            ),
        }],
    )
    return json.loads(message.content[0].text)


def _fallback_reverse_matching(caps: list[dict], demands: list[dict]) -> dict:
    """Fallback: simple text similarity between capabilities and demand descriptions."""
    caps_text = " ".join(
        f"{c['description']} {c.get('device_info', '')} {c['type']}" for c in caps
    ).lower()

    scored = []
    for d in demands:
        demand_text = d["description"].lower()
        score = SequenceMatcher(None, caps_text, demand_text).ratio()
        scored.append({
            "demand_id": d["demand_id"],
            "relevance_score": round(score, 3),
            "reasoning": "Keyword similarity match (fallback)",
        })
    return {"scored_demands": scored}


def find_demands_for_agent(
    db: Session,
    agent: Agent,
    max_results: int = 10,
) -> dict:
    """Reverse semantic search: find open demands that match an agent's capabilities."""
    caps = _build_agent_capabilities_summary(db, agent)
    if not caps:
        return {"results": [], "total_results": 0, "matching_method": "none"}

    candidate_demands = _build_demands_list(
        db, agent, max_demands=settings.max_prefilter_candidates,
    )
    if not candidate_demands:
        return {"results": [], "total_results": 0, "matching_method": "none"}

    caps_json = json.dumps(caps, ensure_ascii=False, indent=2)
    demands_json = json.dumps(candidate_demands, ensure_ascii=False, indent=2)

    try:
        claude_result = _call_claude_for_reverse_matching(caps_json, demands_json)
        method = "claude"
    except Exception as e:
        logger.warning("Claude API failed for reverse matching, using fallback: %s", e)
        claude_result = _fallback_reverse_matching(caps, candidate_demands)
        method = "fallback_keyword"

    scored_map = {
        s["demand_id"]: s for s in claude_result.get("scored_demands", [])
    }

    results = []
    for d in candidate_demands:
        score_info = scored_map.get(d["demand_id"], {})
        results.append({
            "demand_id": d["demand_id"],
            "description": d["description"],
            "bounty_amount": d["bounty_amount"],
            "relevance_score": score_info.get("relevance_score", 0),
            "reasoning": score_info.get("reasoning", ""),
            "distance_km": d["distance_km"],
            "created_at": d["created_at"],
        })

    results.sort(key=lambda r: r["relevance_score"], reverse=True)
    results = results[:max_results]

    return {
        "results": results,
        "total_results": len(results),
        "matching_method": method,
    }
