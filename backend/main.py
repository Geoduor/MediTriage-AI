"""MediTriage AI - FastAPI application entry point.

Person 1 (Lead Developer + DevOps) owns this file.

Run locally:
    cd backend
    uvicorn main:app --reload

The app must start even with no ANTHROPIC_API_KEY and no network: triage is
decided by the deterministic rule engine, and Claude is an enhancement.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import SERVICE_NAME, VERSION, router
from config import get_settings
from knowledge.loader import get_knowledge_base, load_knowledge_base
from llm.client import llm_status

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate the knowledge base at boot so a content error fails fast."""
    logger.info("%s v%s starting", SERVICE_NAME, VERSION)
    status = llm_status()
    logger.info("LLM: %s", status["reason"])
    try:
        kb = load_knowledge_base()
        logger.info("Knowledge base ready: %s", kb.summary())
    except Exception:
        logger.exception(
            "Knowledge base failed to load. Endpoints that need it will return "
            "an error until backend/data/*.json is fixed."
        )
    logger.info("CORS origins: %s", ", ".join(settings.cors_origins))
    yield
    logger.info("%s shutting down", SERVICE_NAME)


app = FastAPI(
    title=SERVICE_NAME,
    version=VERSION,
    description=(
        "AI-assisted symptom triage for Kenya's Primary Care Network.\n\n"
        "Symptoms in, RED / YELLOW / GREEN out, with the care pathway and the "
        "SHA fund that covers it.\n\n"
        "Triage decisions are made by a deterministic rule engine. Claude is "
        "used to structure symptoms and phrase advice, so the service keeps "
        "working without an API key."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["ops"])
def root() -> dict[str, object]:
    """Landing payload so a bare Render URL is not a 404 during judging."""
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
        "demo_scenarios": "/api/demo/test-cases",
        "endpoints": {
            "analyze_symptoms": "POST /api/analyze-symptoms",
            "triage_decision": "POST /api/triage-decision",
            "care_pathway": "POST /api/care-pathway",
            "full_triage": "POST /api/full-triage",
            "rules": "GET /api/rules",
        },
        "llm": llm_status(),
    }


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return readable validation errors - the frontend shows these to users."""
    problems = [
        {
            "field": ".".join(str(part) for part in error.get("loc", []) if part != "body"),
            "message": error.get("msg", "invalid value"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_request",
            "message": "Some of the information sent was not valid.",
            "problems": problems,
        },
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a stack trace to a patient-facing client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Something went wrong. Please try again or speak to a health worker.",
        },
    )


@app.get("/api/status", tags=["ops"])
def detailed_status() -> dict[str, object]:
    """Deeper status than /health, for debugging a live deployment."""
    try:
        kb = get_knowledge_base()
        kb_summary = kb.summary()
        kb_ok = True
    except Exception as exc:
        kb_summary = {"error": str(exc)}
        kb_ok = False
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "settings": settings.describe(),
        "llm": llm_status(),
        "knowledge_base": kb_summary,
        "knowledge_base_ok": kb_ok,
    }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
