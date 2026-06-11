"""
AI Viva Examiner — FastAPI Application
Production-ready entry point with proper middleware, error handling, and logging.
"""
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from app.core.config import settings
from app.core.database import create_tables
from app.core.middleware import RequestIDMiddleware, TimingMiddleware, SecurityHeadersMiddleware
from app.api.routes import auth, submissions, viva, analytics, users, voice

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.APP_ENV == "development" else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("viva_api")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} [{settings.APP_ENV}]")
    await create_tables()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("Database tables ready. Upload directory ensured.")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered project viva examination system.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs"   if settings.APP_ENV == "development" else None,
    redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
    openapi_url="/api/openapi.json" if settings.APP_ENV == "development" else None,
)

# ── Middleware (order matters — outermost first) ───────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{req_id}] Unhandled exception on {request.method} {request.url.path}: {exc}")
    if settings.APP_ENV == "development":
        logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc) if settings.APP_ENV == "development" else "Internal server error.",
            "request_id": req_id,
        }
    )

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api")
app.include_router(users.router,       prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(viva.router,        prefix="/api")
app.include_router(analytics.router,   prefix="/api")
app.include_router(voice.router,       prefix="/api")


# ── Health / readiness ────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/api/ready", tags=["Health"])
async def readiness():
    """Used by load balancers / k8s probes."""
    from app.core.database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not ready", "detail": str(e)})
