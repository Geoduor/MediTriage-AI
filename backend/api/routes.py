"""API routes.

Person 1 (Lead Developer + DevOps) owns this file.

Four endpoints, matching the architecture document:
  POST /api/analyze-symptoms   Agent 1 only
  POST /api/triage-decision    Agent 2 only
  POST /api/care-pathway       Agent 3 only
  POST /api/full-triage        the chained pipeline the frontend uses

Plus GET /health (required by Render) and demo/test helper routes.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from agents.care_pathway import generate_care_pathway
from agents.symptom_analyzer import analyze_symptoms
from agents.triage_router import explain_decision, triage_decision
from api.schemas import (
    AnalyzeSymptomsRequest,
    CarePathwayRequest,
    HealthResponse,
    TriageDecisionRequest,
    TriageRequest,
)
from config import get_settings
from knowledge.loader import get_knowledge_base, reset_knowledge_base_cache
from llm.client import llm_status, probe_llm
from orchestrator import SLA_SECONDS, run_full_triage

logger = logging.getLogger(__name__)
router = APIRouter()

SERVICE_NAME = "MediTriage AI"
VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Liveness and configuration check. Render polls this."""
    settings = get_settings()
    kb = get_knowledge_base()
    summary = kb.summary()
    checks = {
        "knowledge_base_loaded": summary["rules"] > 0 and summary["conditions"] > 0,
        "demo_scenarios_present": summary["demo_scenarios"] >= 5,
        "sha_benefits_present": summary["sha_funds"] == 3,
        "llm_configured": llm_status()["enabled"],
    }
    return HealthResponse(
        status="ok" if checks["knowledge_base_loaded"] else "degraded",
        service=SERVICE_NAME,
        version=VERSION,
        llm=llm_status(),
        knowledge_base=summary,
        checks=checks,
    )


@router.get("/api/demo/test-cases", tags=["demo"])
def list_test_cases() -> dict[str, Any]:
    """The 5 demo scenarios. Lets the frontend and judges drive the demo without typing."""
    kb = get_knowledge_base()
    return {
        "test_cases": [
            {
                "scenario_id": case.get("scenario_id"),
                "patient_name": case.get("patient_name"),
                "patient_age": case.get("patient_age"),
                "sex": case.get("sex"),
                "location": case.get("location"),
                "symptoms": case.get("symptoms"),
                "patient_context": case.get("patient_context", {}),
                "language": case.get("language", "en"),
                "expected_triage_level": case.get("expected_triage_level"),
            }
            for case in kb.test_cases
        ],
        "regression_cases": kb.regression_cases,
    }


@router.post("/api/analyze-symptoms", tags=["agents"])
def analyze(request: AnalyzeSymptomsRequest) -> dict[str, Any]:
    """Agent 1 - extract a structured symptom profile."""
    return analyze_symptoms(
        symptom_text=request.symptoms,
        patient_age=request.patient_age,
        patient_context=request.patient_context.model_dump(),
        sex=request.sex,
        language=request.language,
    )


@router.post("/api/triage-decision", tags=["agents"])
def decide(request: TriageDecisionRequest) -> dict[str, Any]:
    """Agent 2 - decide RED / YELLOW / GREEN from a feature profile."""
    if not request.symptom_profile:
        raise HTTPException(status_code=422, detail="symptom_profile must not be empty")
    result = triage_decision(request.symptom_profile)
    result["explanation"] = explain_decision(result)
    return result


@router.post("/api/care-pathway", tags=["agents"])
def pathway(request: CarePathwayRequest) -> dict[str, Any]:
    """Agent 3 - produce care instructions and SHA cost information."""
    return generate_care_pathway(
        triage_level=request.triage_level,
        symptom_profile=request.symptom_profile,
        language=request.language,
        triage_result=request.triage_result,
    )


@router.post("/api/full-triage", tags=["agents"])
def full_triage(request: TriageRequest) -> dict[str, Any]:
    """The chained pipeline: symptoms -> analysis -> triage -> care pathway."""
    outcome = run_full_triage(
        symptoms=request.symptoms,
        patient_age=request.patient_age,
        patient_context=request.patient_context.model_dump(),
        language=request.language,
        sex=request.sex,
    )
    payload = outcome.to_dict()
    if not payload["audit"]["within_sla"]:
        logger.warning(
            "Triage exceeded the %.0fs target: %sms", SLA_SECONDS, payload["audit"]["total_ms"]
        )
    return payload


@router.get("/api/rules", tags=["ops"])
def list_rules() -> dict[str, Any]:
    """Expose the rule set so a clinician can review the logic."""
    kb = get_knowledge_base()
    return {
        "evaluation": kb.rule_meta.get("evaluation", {}),
        "clinical_notes": kb.rule_meta.get("clinical_notes", []),
        "pilot_todo": kb.rule_meta.get("PILOT_TODO", []),
        "rules": [
            {
                "rule_id": rule.get("rule_id"),
                "name": rule.get("name"),
                "priority": rule.get("priority"),
                "triage_level": rule.get("triage_level"),
                "recommended_pathway": rule.get("recommended_pathway"),
                "sha_fund": rule.get("sha_fund"),
                "rationale": rule.get("rationale"),
                "predicates": rule.get("predicates", []),
            }
            for rule in kb.rules
        ],
    }


@router.post("/api/admin/reload-knowledge-base", tags=["ops"])
def reload_knowledge_base() -> dict[str, Any]:
    """Re-read the JSON knowledge base without a redeploy.

    Person 3 can edit data/*.json and reload rather than waiting for a deploy.
    """
    reset_knowledge_base_cache()
    kb = get_knowledge_base()
    return {"status": "reloaded", "knowledge_base": kb.summary()}


@router.get("/api/admin/llm-check", tags=["ops"])
def llm_check() -> dict[str, Any]:
    """Live probe of the configured LLM provider.

    Why this exists: `llm.enabled` in /health only means "configured". A wrong or
    expired key still reports enabled=true while every request silently falls
    back to the deterministic engine - and on a deployed service the real reason
    is only in the provider's response, which the server log holds. This endpoint
    returns that reason directly, so a misconfigured key is diagnosable from a
    browser.

    Makes one small live call. Never raises.
    """
    result = probe_llm()
    logger.info("LLM probe: ok=%s provider=%s", result["ok"], result["provider"])
    return result
