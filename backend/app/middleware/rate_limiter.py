"""Redis-backed sliding window rate limiter middleware."""
import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.dependencies import get_redis

# Rate limit rules: (path_prefix, method, max_requests, window_seconds, key_type)
# key_type: "ip" = per IP, "user" = per authenticated user
RATE_LIMITS: list[tuple[str, str, int, int, str]] = [
    ("/api/v1/auth/login", "POST", 5, 900, "ip"),          # 5/15min/IP
    ("/api/v1/auth/register", "POST", 3, 3600, "ip"),       # 3/hour/IP
    ("/api/v1/decision/can-afford", "POST", 20, 60, "user"), # 20/min/user
    ("/api/v1/transactions", "POST", 100, 60, "user"),       # 100/min/user
    ("/api/v1/transactions/import-csv", "POST", 5, 3600, "user"),  # 5/hour/user
    ("/api/v1/insights", "GET", 30, 60, "user"),             # 30/min/user
]


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter using Redis sorted sets."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        method = request.method

        # Find matching rate limit rule
        rule = None
        for r_path, r_method, r_max, r_window, r_key_type in RATE_LIMITS:
            if path.startswith(r_path) and method == r_method:
                rule = (r_path, r_method, r_max, r_window, r_key_type)
                break

        if rule is None:
            return await call_next(request)

        _, _, max_requests, window_seconds, key_type = rule

        # Build rate limit key
        if key_type == "ip":
            identifier = request.client.host if request.client else "unknown"
        else:
            # For user-based limits, extract from auth header
            auth_header = request.headers.get("authorization", "")
            identifier = auth_header[-16:] if auth_header else (
                request.client.host if request.client else "unknown"
            )

        redis_key = f"rate_limit:{path}:{method}:{identifier}"

        try:
            redis = await get_redis()
            now = time.time()
            window_start = now - window_seconds

            pipe = redis.pipeline()
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # Count current window entries
            pipe.zcard(redis_key)
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            # Set expiry on the key
            pipe.expire(redis_key, window_seconds + 1)
            results = await pipe.execute()

            current_count = results[1]

            if current_count >= max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many requests. Limit: {max_requests} per {window_seconds}s",
                        },
                    },
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, max_requests - current_count - 1)
            )
            return response

        except Exception:
            # If Redis is down, allow the request through (fail open for availability)
            return await call_next(request)
