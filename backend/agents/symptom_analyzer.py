"""Agent 1 - Symptom Analyzer.

Person 1 (Lead Developer + DevOps) owns this file.

Purpose: turn free-text symptoms (English or Swahili) into a canonical,
structured feature profile.

Two paths, one output shape:
  1. The configured LLM (Gemini by default, see LLM_PROVIDER) extracts the
     structure when available (richer differential list).
  2. The deterministic extractor in `triage/extractor.py` always runs and is
     used outright when no LLM is available, and is also merged in when the
     LLM responds, so the numbers (temperature, duration, red-flag union)
     always come from one place.

This agent must never raise. A failed analysis degrades to the deterministic
profile, which still triages correctly.
"""
from __future__ import annotations

import logging
from typing import Any

from llm.client import call_llm_json, llm_status
from triage.extractor import attach_source_text, canonicalise_profile, extract_features

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a clinical triage assistant supporting primary care \
clinics in Kenya. You extract structured findings from a patient's own words.

Rules:
- Respond with a single JSON object and nothing else. No prose, no markdown fences.
- Never state or imply a definitive diagnosis. You extract findings only.
- Consider Kenya-relevant differentials: malaria, typhoid, tuberculosis,
  pneumonia, HIV-related illness, dehydration from diarrhoeal disease,
  hypertensive emergency, diabetes complications, obstetric emergencies.
- Report only red flags that are actually supported by the text or by the
  patient context. Do not invent danger signs.
- Recognise Swahili and Sheng terms for symptoms."""

USER_TEMPLATE = """Patient context:
- Age: {age}
- Sex: {sex}
- Pregnant: {pregnant}
- Known chronic conditions: {chronic}
- HIV status: {hiv_status}
- Location (county): {location}

Patient's own words:
\"\"\"{symptoms}\"\"\"

Return a JSON object with exactly these keys:
{{
  "primary_symptom": "snake_case main complaint",
  "associated_symptoms": ["snake_case", "..."],
  "duration_days": <integer or null>,
  "severity": "mild" | "moderate" | "severe" | "unknown",
  "red_flags": ["danger signs actually present in the text"],
  "temperature_celsius": <number or null>,
  "differential_considerations": ["up to 4 Kenya-relevant possibilities"],
  "clinical_summary": "one neutral sentence describing the presentation"
}}"""


def _patient_context(
    age: int | None,
    sex: str | None,
    patient_context: dict[str, Any] | None,
) -> dict[str, Any]:
    context = dict(patient_context or {})
    return {
        "age": age if age is not None else context.get("age"),
        "sex": sex or context.get("sex"),
        "pregnant": bool(context.get("pregnant", False)),
        "chronic": context.get("chronic_conditions") or context.get("chronic") or [],
        "hiv_status": context.get("hiv_status"),
        "location": context.get("location") or context.get("county"),
    }


def analyze_symptoms(
    symptom_text: str,
    patient_age: int | None = None,
    patient_context: dict[str, Any] | None = None,
    sex: str | None = None,
    language: str = "en",
    use_llm: bool | None = None,
) -> dict[str, Any]:
    """Analyze symptoms and return a canonical feature profile.

    `use_llm=False` forces the deterministic path (used by tests and by
    LLM_MODE=off).
    """
    raw_text = symptom_text or ""

    # Path 2 first: this always runs and is the fallback of record.
    deterministic = extract_features(raw_text, patient_age, patient_context)

    status = llm_status()
    should_call_llm = status["enabled"] if use_llm is None else (use_llm and status["enabled"])

    if not should_call_llm:
        profile = attach_source_text(deterministic, raw_text)
        profile["extraction_method"] = "deterministic"
        profile["llm_used"] = False
        profile["analysis_notes"] = status["reason"]
        return profile

    context = _patient_context(patient_age, sex, patient_context)
    prompt = USER_TEMPLATE.format(
        age=context["age"] if context["age"] is not None else "not given",
        sex=context["sex"] or "not given",
        pregnant="yes" if context["pregnant"] else "no",
        chronic=", ".join(str(item) for item in context["chronic"]) or "none reported",
        hiv_status=context["hiv_status"] or "not given",
        location=context["location"] or "not given",
        symptoms=raw_text,
    )
    if language == "sw":
        prompt += "\n\nThe patient wrote in Swahili. Keep snake_case keys in English."

    parsed = call_llm_json(SYSTEM_PROMPT, prompt, max_tokens=700)

    if not parsed:
        profile = attach_source_text(deterministic, raw_text)
        profile["extraction_method"] = "deterministic"
        profile["llm_used"] = False
        profile["analysis_notes"] = "The LLM returned nothing usable; deterministic extractor used."
        return profile

    # Merge the model's narrative findings with the deterministic numbers, then
    # canonicalise so downstream rules see one consistent shape.
    merged_input: dict[str, Any] = {
        **parsed,
        "source_text": raw_text,
        "patient_context": patient_context or {},
        "extraction_method": f"llm:{status['provider']}",
        "extraction_confidence": 0.85,
    }
    profile = canonicalise_profile(merged_input)
    profile = attach_source_text(profile, raw_text)
    profile["llm_used"] = True
    profile["llm_model"] = status["model"]
    profile["analysis_notes"] = "LLM extraction merged with deterministic verification."
    # If the model found fewer symptoms than the keyword scan, keep the union so
    # a missed symptom cannot lower the triage level.
    for symptom in deterministic.get("all_symptoms", []):
        if symptom not in profile["all_symptoms"]:
            profile["all_symptoms"].append(symptom)
    if profile["primary_symptom"] in {"unspecified", ""} and deterministic.get("primary_symptom"):
        profile["primary_symptom"] = deterministic["primary_symptom"]
    return profile
