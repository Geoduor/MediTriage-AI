"""Agent 2 - Triage Router.

Person 1 (Lead Developer + DevOps) owns this file.

Deliberately rule-based and LLM-free. The original architecture document called
for this and it is the right call: an urgency decision shown to a patient must
be reproducible, auditable and explainable. Claude proposes structure (Agent 1);
this agent disposes.
"""
from __future__ import annotations

import logging
from typing import Any

from knowledge.loader import KnowledgeBase, get_knowledge_base
from triage.engine import RuleMatch, triage

logger = logging.getLogger(__name__)


def triage_decision(
    symptom_profile: dict[str, Any],
    knowledge_base: KnowledgeBase | None = None,
) -> dict[str, Any]:
    """Decide RED / YELLOW / GREEN from a canonical feature profile.

    Pure function of (profile, rules): the same input always yields the same
    level, which is what makes the demo reproducible and the logic reviewable by
    a clinician.
    """
    kb = knowledge_base or get_knowledge_base()
    match: RuleMatch = triage(symptom_profile, kb.rules, kb.rule_meta)

    result = match.to_dict()
    result["agent"] = "triage_router"
    result["rules_evaluated"] = len(kb.rules)
    result["patient_summary"] = _patient_summary(symptom_profile)
    logger.info(
        "Triage decision: level=%s rule=%s fund=%s",
        match.triage_level,
        match.rule_id,
        match.sha_fund,
    )
    return result


def _patient_summary(profile: dict[str, Any]) -> str:
    """One-line, human-readable summary used in logs and on the referral slip."""
    primary = str(profile.get("primary_symptom", "unspecified")).replace("_", " ")
    associated = [str(item).replace("_", " ") for item in profile.get("associated_symptoms", [])]
    duration_days = profile.get("duration_days")
    severity = profile.get("severity", "unknown")

    parts = [primary]
    if associated:
        parts.append("with " + ", ".join(associated[:4]))
    if duration_days is not None:
        parts.append(f"for {duration_days} day(s)")
    parts.append(f"severity {severity}")
    return ", ".join(parts) + "."


def explain_decision(result: dict[str, Any]) -> list[str]:
    """Bullet points explaining why this level was chosen, for the clinician UI."""
    lines: list[str] = []
    matched = result.get("matched_rule", {})
    lines.append(f"Matched rule {matched.get('rule_id')}: {matched.get('name')}")
    if result.get("rationale"):
        lines.append(str(result["rationale"]))
    if result.get("sha_fund"):
        lines.append(f"SHA fund applicable: {result['sha_fund']}")
    for alternative in result.get("alternatives", []):
        lines.append(
            f"Also matched {alternative.get('rule_id')} ({alternative.get('triage_level')}) "
            f"- the higher-acuity rule was applied."
        )
    return lines
