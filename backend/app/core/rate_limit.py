import time
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException, status
from backend.app.core.errors import NutriLensException

class InMemoryRateLimiter:
    """
    Token-bucket / Sliding window rate limiter (SDD Section 28 lines 1833, Section 33 Phase 11).
    Enforces per-user / per-IP quotas and injects X-RateLimit-* response headers.
    Redis-compatible interface designed for drop-in distributed clustering.
    """
    def __init__(self):
        # key -> list of timestamp floats
        self._history: Dict[str, list] = {}

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Evaluates rate limit for a key.
        Returns: (allowed: bool, remaining: int, reset_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds

        # Clean history
        records = [t for t in self._history.get(key, []) if t > window_start]
        self._history[key] = records

        remaining = max(0, limit - len(records))
        reset_seconds = int(window_seconds - (now - records[0])) if records else window_seconds

        if len(records) >= limit:
            return False, 0, max(1, reset_seconds)

        # Record this request
        records.append(now)
        self._history[key] = records
        return True, remaining - 1, max(1, reset_seconds)

    def reset_key(self, key: str):
        if key in self._history:
            del self._history[key]

# Global singleton
rate_limiter = InMemoryRateLimiter()

def rate_limit_guard(
    limit: int = 30,
    window_seconds: int = 3600,
    quota_name: str = "food_analyze"
):
    """
    FastAPI dependency enforcing per-user quota (e.g. 30 scans/hour on /food/analyze).
    """
    async def dependency(request: Request):
        # Determine client identifier: Auth user ID if present, otherwise client IP
        auth_header = request.headers.get("Authorization", "")
        client_ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get("X-User-ID") or (auth_header[:32] if auth_header else client_ip)
        key = f"{quota_name}:{user_id}"

        allowed, remaining, reset_sec = rate_limiter.is_allowed(key, limit, window_seconds)

        # Attach headers to request state to be injected in response middleware
        request.state.rate_limit_limit = limit
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_reset = reset_sec

        if not allowed:
            raise NutriLensException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded for quota '{quota_name}'. Maximum {limit} requests per {window_seconds}s.",
                details={"limit": limit, "remaining": 0, "reset_in_seconds": reset_sec},
            )
        return True

    return dependency
