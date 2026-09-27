"""Agent 3 - Care Pathway Recommender.

Person 1 (Lead Developer + DevOps) owns this file.

Turns a triage decision plus a feature profile into concrete next steps: where
to go, what it costs under SHA, what to bring, what to do right now, and which
danger signs mean come back immediately.

The clinical skeleton always comes from JSON (`sha_benefits.json`,
`conditions.json`, `swahili_translations.json`). The configured LLM (Gemini by
default, see LLM_PROVIDER) is used only to phrase the instruction more warmly
and patient-specifically - if it is unavailable the template output is already
complete and correct.

SHA matters here: NHIF was replaced in October 2024, so every cost statement
names a SHA fund rather than an NHIF scheme.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from knowledge.loader import KnowledgeBase, get_knowledge_base
from llm.client import call_llm, llm_status

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You write short, kind care instructions for patients at \
primary care clinics in Kenya. You are not diagnosing; you are explaining what \
the patient should do next.

Rules:
- Use sentences of 6-8 words. No medical jargon.
- Write in the requested language only.
- Be calm and direct. Never blame or frighten the patient.
- Do not change the urgency level you are given, and do not add or remove
  clinical advice.
- Do not invent costs. Restate only the coverage information supplied.
- Plain text only: no markdown, no headings, no bullet characters."""

PATHWAY_FACILITY: dict[str, str] = {
    "hospital": "sub_county_hospital",
    "mental_health_crisis": "sub_county_hospital",
    "clinic": "health_centre",
    "mental_health": "health_centre",
    "home_or_clinic": "dispensary",
}

DEFAULT_DANGER_SIGNS: dict[str, list[str]] = {
    "RED": ["becoming unconscious", "difficulty breathing", "worsening pain", "cold sweat"],
    "YELLOW": ["difficulty breathing", "confusion", "unable to drink", "symptoms getting worse"],
    "GREEN": ["difficulty breathing", "fever that will not go down", "unable to drink", "symptoms lasting more than five days"],
}

# Keywords used to attach a knowledge-base condition to the presentation. This
# only personalises wording and danger signs; it never affects the triage level.
CONDITION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "malaria": ("fever", "chills", "malaria", "homa"),
    "chest_pain": ("chest_pain", "chest pain", "cardiac"),
    "depression_anxiety": ("depress", "anxiety", "suicidal", "mental", "sad"),
    "respiratory_infection": ("cough", "breathing", "throat", "nose"),
    "diarrhoea": ("diarrhoea", "diarrhea", "vomit", "stool"),
    "hypertension": ("hypertension", "blood_pressure", "blood pressure"),
    "diabetes": ("diabetes", "diabetic", "sugar", "thirst"),
    "uti": ("urinary", "urine", "dysuria", "mkojo"),
    "skin_infection": ("skin", "rash", "wound", "ulcer"),
    "minor_injury": ("injury", "cut", "bruise", "sprain", "fracture"),
}


def _match_condition(profile: dict[str, Any], kb: KnowledgeBase) -> dict[str, Any] | None:
    haystack_parts = [
        str(profile.get("primary_symptom", "")),
        " ".join(str(item) for item in profile.get("associated_symptoms", [])),
        " ".join(str(item) for item in profile.get("all_symptoms", [])),
    ]
    haystack = " ".join(haystack_parts).lower().replace("_", " ")

    best: tuple[int, dict[str, Any]] | None = None
    for slug, keywords in CONDITION_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.replace("_", " ") in haystack)
        if score == 0:
            continue
        condition = kb.condition_by_slug(slug)
        if condition and (best is None or score > best[0]):
            best = (score, condition)
    return best[1] if best else None


def _fund_block(kb: KnowledgeBase, fund_code: str | None) -> dict[str, Any]:
    if not fund_code:
        fund_code = "PHF"
    fund = kb.fund(fund_code) or kb.fund("PHF") or {}
    return {
        "code": fund.get("code", fund_code),
        "name": fund.get("name", fund_code),
        "covers": fund.get("covers", []),
        "patient_cost": fund.get("patient_cost", ""),
    }


def _cost_statement(kb: KnowledgeBase, fund_code: str | None, level: str) -> dict[str, str | None]:
    cost = kb.swahili.get("cost", {})
    if fund_code == "ECCIF":
        return {
            "en": "Emergency and critical care is covered by SHA through the Emergency, Chronic and Critical Illness Fund. Expect little or no cost.",
            "sw": cost.get("covered_eccif"),
        }
    if fund_code == "SHIF":
        return {
            "en": "This care is covered by SHA through the Social Health Insurance Fund. A small registration or medicine co-pay may apply.",
            "sw": cost.get("covered_shif"),
        }
    if level == "GREEN":
        return {
            "en": "No clinic visit is needed now. If you do attend a dispensary or health centre, this is free under the SHA Primary Healthcare Fund - you pay only transport.",
            "sw": cost.get("transport_only"),
        }
    return {
        "en": "This is free at a dispensary or health centre under the SHA Primary Healthcare Fund. You pay only transport.",
        "sw": cost.get("free_phf"),
    }


def _default_instructions(level: str, condition: dict[str, Any] | None) -> dict[str, list[str]]:
    """Template instructions, used directly when Claude is unavailable."""
    condition_name = (condition or {}).get("name", "")
    if level == "RED":
        english = [
            "Go to the nearest hospital immediately.",
            "Do not drive yourself. Ask someone to take you, or call for emergency transport.",
            "Tell the staff you have SHA cover - emergency care is covered.",
        ]
        swahili = [
            "Nenda hospitalini mara moja.",
            "Usiendeshe gari mwenyewe. Omba mtu akuchukue.",
            "Waambie una bima ya SHA.",
        ]
        if condition_name == "Chest Pain":
            english.insert(1, "Stop all activity and sit down. Chew 325 mg aspirin if you have it and are not allergic.")
            swahili.insert(1, "Acha shughuli zote na uketi chini. Tafuna aspirini ikiwa unayo na huna mzio.")
    elif level == "YELLOW":
        english = [
            "Go to the nearest health centre or clinic today.",
            "Bring your SHA card or ID.",
            "Drink fluids and rest while you wait to be seen.",
        ]
        swahili = [
            "Nenda kituo cha afya kilicho karibu leo.",
            "Leta kadi yako ya SHA au kitambulisho.",
            "Kunywa maji na upumzike wakati unasubiri.",
        ]
    else:
        english = [
            "You can manage this at home for now.",
            "Rest and drink plenty of fluids.",
            "Take paracetamol if you have a fever or pain.",
            "Come to a clinic if you are not better in three days.",
        ]
        swahili = [
            "Unaweza kujitunza nyumbani kwa sasa.",
            "Pumzika na kunywa maji mengi.",
            "Kunywa paracetamol ikiwa una homa au maumivu.",
            "Nenda kliniki ikiwa hupati nafuu baada ya siku tatu.",
        ]

    if condition:
        # Template actions often restate the condition's self-care in different
        # words ("Chew 325 mg aspirin if you have it and are not allergic" vs
        # "Chew aspirin (325mg) if available"), so an exact-substring check is
        # not enough. Compare on meaningful token overlap instead: otherwise the
        # patient is told to chew aspirin twice on a cardiac emergency slip.
        existing = [set(_significant_tokens(item)) for item in english]
        for item in (condition.get("self_care") or [])[:3]:
            candidate = str(item).strip()
            if not candidate:
                continue
            tokens = set(_significant_tokens(candidate))
            if tokens and any(tokens & seen for seen in existing):
                continue
            english.append(candidate + ".")
            existing.append(tokens)
    return {"en": english, "sw": swahili}


_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "if", "is", "are", "it", "you", "your",
        "all", "any", "to", "of", "in", "on", "for", "with", "not", "no",
        "available", "immediately", "now", "take", "get", "keep", "do",
    }
)


def _significant_tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens with stopwords and short words removed."""
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", str(text).lower())
    return [
        token
        for token in cleaned.split()
        if len(token) >= 3 and token not in _STOPWORDS
    ]


def _danger_signs(level: str, condition: dict[str, Any] | None, kb: KnowledgeBase) -> list[str]:
    signs = list((condition or {}).get("danger_signs_watch") or [])
    if not signs:
        signs = DEFAULT_DANGER_SIGNS.get(level, DEFAULT_DANGER_SIGNS["GREEN"])
    return signs[:5]


def _personalise_with_llm(
    level: str,
    profile: dict[str, Any],
    language: str,
    base_instructions: list[str],
    cost_en: str,
) -> str | None:
    status = llm_status()
    if not status["enabled"]:
        return None

    language_name = "Swahili" if language == "sw" else "English"
    prompt = f"""Urgency level: {level}
Patient presentation: {profile.get('primary_symptom', 'unspecified')}, severity {profile.get('severity', 'unknown')}
Cost information to restate: {cost_en}
Base actions that must all be preserved: {' | '.join(base_instructions)}

Write 3 short sentences in {language_name} telling this patient what to do next.
Use no markdown and no bullet points."""
    return call_llm(SYSTEM_PROMPT, prompt, max_tokens=250, temperature=0.2)


def generate_care_pathway(
    triage_level: str,
    symptom_profile: dict[str, Any],
    language: str = "en",
    triage_result: dict[str, Any] | None = None,
    knowledge_base: KnowledgeBase | None = None,
    use_llm: bool | None = None,
) -> dict[str, Any]:
    """Build the care pathway. Never raises; degrades to templates."""
    kb = knowledge_base or get_knowledge_base()
    language = "sw" if str(language).lower().startswith("sw") else "en"
    result = triage_result or {}
    pathway = result.get("recommended_pathway") or "clinic"
    fund_code = result.get("sha_fund")

    condition = _match_condition(symptom_profile, kb)
    facility_level = PATHWAY_FACILITY.get(pathway, "health_centre")
    facility = next(
        (item for item in kb.facility_levels() if item.get("level") == facility_level),
        {"level": facility_level, "services": [], "patient_cost_kes": "unknown"},
    )
    fund = _fund_block(kb, fund_code)
    cost = _cost_statement(kb, fund_code, triage_level)
    instructions = _default_instructions(triage_level, condition)
    danger_signs = _danger_signs(triage_level, condition, kb)

    swahili = kb.swahili
    level_labels = swahili.get("triage_levels", {}).get(triage_level, {})

    personalised: str | None = None
    if use_llm is not False:
        personalised = _personalise_with_llm(
            triage_level,
            symptom_profile,
            language,
            instructions["en"],
            str(cost["en"]),
        )

    if personalised:
        patient_instruction = personalised
        instruction_source = "llm"
    else:
        patient_instruction = " ".join(instructions[language])
        instruction_source = "template"

    return {
        "triage_level": triage_level,
        "language": language,
        "headline": level_labels.get(f"label_{language}") or result.get("label_en", ""),
        "patient_instruction": patient_instruction,
        "instruction_source": instruction_source,
        "actions": language_instructions if personalised else instructions[language],
        "actions_all_languages": instructions,
        "facility": {
            "level": facility.get("level"),
            "name": _facility_display_name(facility.get("level", "")),
            "services": facility.get("services", []),
        },
        "sha": {
            **fund,
            "fund_code": fund["code"],
        },
        "cost": {
            "statement": cost[language] or cost["en"],
            "statement_en": cost["en"],
            "statement_sw": cost["sw"],
            "patient_pays_kes": facility.get("patient_cost_kes", "unknown"),
        },
        "what_to_bring": ["SHA card or ID", "Any medicines you are already taking"],
        "danger_signs_to_watch": danger_signs,
        "follow_up": _follow_up(triage_level),
        "possible_condition": condition.get("name") if condition else None,
        "condition_slug": condition.get("slug") if condition else None,
        "clinical_reviewed": bool(condition.get("clinical_reviewed", False)) if condition else False,
        "disclaimer": swahili.get("reassurance", {}).get("not_a_diagnosis")
        if language == "sw"
        else "This is guidance only, not a diagnosis. A health worker will examine you.",
        "agent": "care_pathway",
    }


def _facility_display_name(level: str) -> str:
    return {
        "dispensary": "Nearest dispensary",
        "health_centre": "Nearest health centre",
        "sub_county_hospital": "Nearest sub-county hospital",
        "referral_hospital": "Referral hospital",
    }.get(level, level.replace("_", " ").title())


def _follow_up(level: str) -> str:
    if level == "RED":
        return "Do not wait for the fever to settle. Go now."
    if level == "YELLOW":
        return "If you cannot reach a clinic today, go first thing tomorrow morning."
    return "If you are not better in three days, or you get worse, go to a clinic."
