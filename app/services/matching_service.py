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
