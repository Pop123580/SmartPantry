"""SmartPantry API — application factory and wiring.

    React + Vite frontend → FastAPI → PostgreSQL (+ AWS Bedrock/Textract/S3)

Docs live at ``/docs``; the OpenAPI schema at ``/openapi.json``.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analytics, auth, pantry, purchases, receipt, recipes, shopping
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("smartpantry")

settings = get_settings()

app = FastAPI(
    title="SmartPantry API",
    version="1.0.0",
    description=(
        "Backend for the SmartPantry frontend: JWT auth, pantry CRUD with a "
        "deterministic food-risk engine, Bedrock recipe generation, "
        "inventory-aware shopping with checkout, and Textract receipt OCR.\n\n"
        "All user-scoped endpoints take the user identity **only** from the "
        "Bearer JWT."
    ),
    contact={"name": "SmartPantry"},
)

# ── CORS: local Vite dev server + configurable production origin ─────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(pantry.router)
app.include_router(recipes.router)
app.include_router(shopping.router)
app.include_router(receipt.router)
app.include_router(purchases.router)
app.include_router(analytics.router)


# ── Health ───────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "SmartPantry API", "docs": "/docs"}


@app.get(
    "/api/health",
    tags=["health"],
    summary="Liveness/readiness probe",
    description="Returns feature availability so clients (and ops) can see "
    "which AWS-backed features are active without calling them.",
)
def health() -> dict:
    # No secrets, no internals — feature availability only.
    return {
        "status": "ok",
        "environment": settings.environment,
        "aws": {
            "bedrock_configured": bool(settings.bedrock_model_id),
            "s3_configured": bool(settings.aws_s3_bucket),
            "region": settings.aws_region,
        },
    }


# ── Error handling — never leak stack traces or secrets ─────────────
@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
