import math

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.capability import Capability


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lon, max_lon) for a rough bounding box."""
    delta_lat = radius_km / 111.0
    delta_lon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon)


def filter_agents_by_distance(
    db: Session,
    ref_lat: float,
    ref_lon: float,
    max_km: float,
) -> list[tuple[Agent, float]]:
    """Return agents within max_km, sorted by distance."""
    min_lat, max_lat, min_lon, max_lon = bounding_box(ref_lat, ref_lon, max_km)
    agents = (
        db.query(Agent)
        .filter(
            Agent.latitude.isnot(None),
            Agent.latitude >= min_lat,
            Agent.latitude <= max_lat,
            Agent.longitude >= min_lon,
            Agent.longitude <= max_lon,
        )
        .all()
    )
    results = []
    for agent in agents:
        dist = haversine_distance(ref_lat, ref_lon, agent.latitude, agent.longitude)
        if dist <= max_km:
            results.append((agent, dist))
    results.sort(key=lambda x: x[1])
    return results
