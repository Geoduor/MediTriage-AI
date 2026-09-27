"""Agent orchestrator - the end-to-end triage pipeline.

Person 1 (Lead Developer + DevOps) owns this file.

Flow:
    raw symptoms
      -> Agent 1  symptom_analyzer   (Claude when available, deterministic always)
      -> Agent 2  triage_router      (pure rules - never an LLM)
      -> Agent 3  care_pathway       (templates + optional Claude phrasing)
      -> response

Guarantees this module is responsible for:
  * the whole pipeline is timed, and the timing is reported back,
  * any agent failure degrades to the deterministic path rather than a 500,
  * the product requirement (<30s) is measured and surfaced, not assumed.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agents.care_pathway import generate_care_pathway
from agents.symptom_analyzer import analyze_symptoms
from agents.triage_router import explain_decision, triage_decision
from knowledge.loader import KnowledgeBase, get_knowledge_base
from llm.client import llm_status

logger = logging.getLogger(__name__)

SLA_SECONDS = 30.0


@dataclass
class TriageOutcome:
    """Full result of a triage run."""

    triage: dict[str, Any]
    symptom_analysis: dict[str, Any]
    care_pathway: dict[str, Any]
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "triage": self.triage,
            "symptom_analysis": self.symptom_analysis,
            "care_pathway": self.care_pathway,
            "audit": self.audit,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_full_triage(
    symptoms: str,
    patient_age: int | None = None,
    patient_context: dict[str, Any] | None = None,
    language: str = "en",
    sex: str | None = None,
    knowledge_base: KnowledgeBase | None = None,
    use_llm: bool | None = None,
) -> TriageOutcome:
    """Run the complete pipeline. This is the function the API and tests call."""
    started = time.perf_counter()
    kb = knowledge_base or get_knowledge_base()
    steps: list[dict[str, Any]] = []
    degraded: list[str] = []

    # --- Agent 1 -----------------------------------------------------------
    step_start = time.perf_counter()
    agent_1_ok = True
    try:
        analysis = analyze_symptoms(
            symptom_text=symptoms,
            patient_age=patient_age,
            patient_context=patient_context,
            sex=sex,
            language=language,
            use_llm=use_llm,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Agent 1 failed; falling back to a fail-safe profile.")
        degraded.append(f"agent_1:{type(exc).__name__}")
        agent_1_ok = False
        analysis = _minimal_profile(symptoms, patient_age, patient_context, sex)
    steps.append({"step": "agent_1_symptom_analyzer", "ms": _ms(step_start), "ok": agent_1_ok})

    # --- Agent 2 -----------------------------------------------------------
    step_start = time.perf_counter()
    agent_2_ok = True
    try:
        triage_result = triage_decision(analysis, knowledge_base=kb)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Agent 2 failed; defaulting to the safest level.")
        degraded.append(f"agent_2:{type(exc).__name__}")
        agent_2_ok = False
        triage_result = _fail_safe_triage()

    # A profile that could not be analysed must never be downgraded to GREEN.
    floor = analysis.get("force_minimum_level")
    if floor and _level_rank(triage_result.get("triage_level")) < _level_rank(floor):
        triage_result = {
            **triage_result,
            "triage_level": floor,
            "urgency": "URGENT",
            "rationale": "The symptom description could not be analysed reliably, so this case is treated as urgent and must be reviewed by a health worker.",
            "matched_rule": {"rule_id": "safety-floor", "name": "Unanalysable presentation floor"},
            "colour": "#f9a825",
            "label_en": "URGENT - go to the clinic today",
            "label_sw": "HARAKA - nenda kliniki leo",
            "engine": "safety-floor",
        }
        degraded.append("safety_floor_applied")

    triage_result["explanation"] = explain_decision(triage_result)
    steps.append({"step": "agent_2_triage_router", "ms": _ms(step_start), "ok": agent_2_ok})

    # --- Agent 3 -----------------------------------------------------------
    step_start = time.perf_counter()
    agent_3_ok = True
    try:
        pathway = generate_care_pathway(
            triage_level=str(triage_result.get("triage_level", "YELLOW")),
            symptom_profile=analysis,
            language=language,
            triage_result=triage_result,
            knowledge_base=kb,
            use_llm=use_llm,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Agent 3 failed; returning a minimal safe pathway.")
        degraded.append(f"agent_3:{type(exc).__name__}")
        agent_3_ok = False
        pathway = _fail_safe_pathway(triage_result)
    steps.append({"step": "agent_3_care_pathway", "ms": _ms(step_start), "ok": agent_3_ok})

    total_ms = _ms(started)
    audit = {
        "requested_at": _now_iso(),
        "total_ms": total_ms,
        "sla_seconds": SLA_SECONDS,
        "within_sla": total_ms / 1000.0 <= SLA_SECONDS,
        "steps": steps,
        "degraded_components": degraded,
        "llm": llm_status(),
        "knowledge_base": kb.summary(),
        "deterministic_core": True,
    }

    return TriageOutcome(
        triage=triage_result,
        symptom_analysis=analysis,
        care_pathway=pathway,
        audit=audit,
    )


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


_LEVEL_RANK = {"GREEN": 0, "YELLOW": 1, "RED": 2}


def _level_rank(level: Any) -> int:
    """Acuity ordering, used to enforce safety floors."""
    return _LEVEL_RANK.get(str(level), 1)


def _minimal_profile(
    symptoms: str,
    patient_age: int | None,
    patient_context: dict[str, Any] | None,
    sex: str | None,
) -> dict[str, Any]:
    """Last-resort profile if the extractor itself blows up.

    Reporting no symptoms would let the rules return GREEN, which is the unsafe
    direction. An unanalysable presentation is escalated to YELLOW instead.
    """
    return {
        "primary_symptom": "unspecified",
        "associated_symptoms": [],
        "all_symptoms": [],
        "duration_days": None,
        "duration_known": False,
        "severity": "unknown",
        "red_flags": [],
        "features": {"fever_present": False, "fever_high": False, "has_red_flag": False},
        "patient": {
            "age": patient_age,
            "pregnant": bool((patient_context or {}).get("pregnant")),
            "chronic": [],
            "hiv_status": (patient_context or {}).get("hiv_status"),
        },
        "source_text": symptoms or "",
        "extraction_method": "failed",
        "extraction_confidence": 0.0,
        "force_minimum_level": "YELLOW",
    }


def _fail_safe_triage() -> dict[str, Any]:
    """If the rule engine is unusable, escalate rather than reassure."""
    return {
        "triage_level": "YELLOW",
        "urgency": "URGENT",
        "rationale": "The triage engine could not be evaluated, so this case is treated as urgent and must be reviewed by a health worker.",
        "recommended_pathway": "clinic",
        "sha_fund": "PHF",
        "matched_rule": {"rule_id": "fail-safe", "name": "Engine fail-safe"},
        "colour": "#f9a825",
        "label_en": "URGENT - go to the clinic today",
        "label_sw": "HARAKA - nenda kliniki leo",
        "target_time": "within 24 hours",
        "engine": "fail-safe",
        "alternatives": [],
        "confidence": 0.0,
        "agent": "triage_router",
    }


def _fail_safe_pathway(triage_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "triage_level": triage_result.get("triage_level", "YELLOW"),
        "language": "en",
        "headline": "URGENT - go to the clinic today",
        "patient_instruction": "Go to the nearest clinic today and show this slip to a health worker.",
        "instruction_source": "fail-safe",
        "actions": ["Go to the nearest clinic today.", "Show this slip to a health worker."],
        "facility": {"level": "health_centre", "name": "Nearest health centre", "services": []},
        "sha": {"code": "PHF", "name": "Primary Healthcare Fund", "covers": [], "patient_cost": ""},
        "cost": {"statement": "Care at a dispensary or health centre is free under SHA.", "patient_pays_kes": "0"},
        "what_to_bring": ["SHA card or ID"],
        "danger_signs_to_watch": ["difficulty breathing", "confusion", "symptoms getting worse"],
        "follow_up": "If you cannot reach a clinic today, go first thing tomorrow morning.",
        "possible_condition": None,
        "condition_slug": None,
        "clinical_reviewed": False,
        "disclaimer": "This is guidance only, not a diagnosis.",
        "agent": "care_pathway",
    }
