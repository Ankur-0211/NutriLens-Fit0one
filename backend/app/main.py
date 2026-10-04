import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.errors import NutriLensException, error_response
from backend.app.modules.health.router import router as health_router
from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.nutrition.router import router as nutrition_router
from backend.app.modules.identity_resolution.router import router as identity_router
from backend.app.modules.recognition.router import router as recognition_router
from backend.app.modules.analysis.router import router as analysis_router
from backend.app.modules.corrections.router import router as corrections_router
from backend.app.modules.meals.router import router as meals_router
from backend.app.modules.improvement.router import router as improvement_router
from backend.app.modules.optimization.router import router as optimization_router
from backend.app.modules.compliance.router import router as compliance_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Timing Middleware as required by SDD Section 40.11
@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    # Inject X-RateLimit headers if set by rate_limit_guard (SDD Section 21.1 / 33 Phase 11)
    if hasattr(request.state, "rate_limit_limit"):
        response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

    return response

# Standard NutriLens Error Envelope Handler (SDD Section 21.1)
@app.exception_handler(NutriLensException)
async def nutrilens_exception_handler(request: Request, exc: NutriLensException):
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    return error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=req_id,
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message=str(exc),
        status_code=500,
        request_id=req_id,
    )

# Include Routers under API V1 prefix
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(health_router)  # also at /health for root health check
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(nutrition_router, prefix=settings.API_V1_STR)
app.include_router(identity_router, prefix=settings.API_V1_STR)
app.include_router(recognition_router, prefix=settings.API_V1_STR)
app.include_router(analysis_router, prefix=settings.API_V1_STR)
app.include_router(corrections_router, prefix=settings.API_V1_STR)
app.include_router(meals_router, prefix=settings.API_V1_STR)
app.include_router(improvement_router, prefix=settings.API_V1_STR)
app.include_router(optimization_router, prefix=settings.API_V1_STR)
app.include_router(compliance_router, prefix=settings.API_V1_STR)
app.include_router(compliance_router)  # for root /metrics Prometheus scrape

# Mount Mobile Flutter application (PWA)
MOBILE_DIR = Path(__file__).resolve().parent.parent.parent / "mobile" / "build" / "web"
if MOBILE_DIR.exists():
    app.mount("/mobile", StaticFiles(directory=str(MOBILE_DIR), html=True), name="mobile")

# Mount Frontend application
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
