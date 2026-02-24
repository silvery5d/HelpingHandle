from fastapi import Request
from slowapi import Limiter


def _get_real_ip(request: Request) -> str:
    """Extract real client IP from X-Forwarded-For (behind Nginx)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_api_key(request: Request) -> str:
    """Use API key as rate limit key for authenticated endpoints."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    return _get_real_ip(request)


# Per-agent limiter: keyed by API key
limiter = Limiter(key_func=_get_api_key)

# Per-IP limiter: for unauthenticated endpoints (registration)
ip_limiter = Limiter(key_func=_get_real_ip)
