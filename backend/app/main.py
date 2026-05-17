"""FastAPI application factory — single entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.dependencies import close_redis, engine
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize and tear down resources."""
    # Startup: nothing extra needed — engine + redis are lazy
    yield
    # Shutdown: dispose connections
    await engine.dispose()
    await close_redis()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        # Disable docs in production (FASTAPI-OPENAPI-001)
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # ── Middleware (order matters — outermost first) ──
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Routers ──
    from app.api.v1.router import api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    # ── Health check ──
    @app.get("/health", include_in_schema=False)
    async def health_check():
        return {"status": "ok", "version": settings.app_version}

    return app


# Module-level app for uvicorn
app = create_app()
