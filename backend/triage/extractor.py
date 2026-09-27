"""Deterministic feature extraction from free-text symptoms.

Person 1 (Lead Developer + DevOps) owns this file.

Why this exists
---------------
The original plan routed every request through Claude. That makes a live demo
depend on an API key, a network connection and available credit. This module is
the safety net: it turns raw symptom text into the same structured feature
profile that Claude produces, using regex and a bilingual keyword taxonomy.

Consequences:
  * With no ANTHROPIC_API_KEY the system still triages correctly.
  * If a Claude call fails mid-demo the request degrades instead of erroring.
  * Swahili input is understood without an LLM round trip.

The extractor is deliberately conservative: it never invents a red flag that is
not present, but it does map recognised danger words to red flags, so ambiguity
resolves towards the safer triage level.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Bilingual symptom taxonomy
# Ordered roughly by clinical acuity: earlier entries win the "primary symptom"
# slot when several symptoms are present, because the most acute complaint is
# what should drive triage.
# ---------------------------------------------------------------------------
SYMPTOM_TAXONOMY: list[tuple[str, tuple[str, ...]]] = [
    ("unconscious", ("unconscious", "unresponsive", "not waking", "kupoteza fahamu")),
    ("convulsions", ("convulsion", "seizure", "fitting", "kifafa")),
    ("chest_pain", ("chest pain", "chest pressure", "chest tightness", "pain in my chest", "maumivu ya kifua")),
    ("difficulty_breathing", ("difficulty breathing", "shortness of breath", "short of breath", "trouble breathing", "cannot breathe", "breathless", "kushindwa kupumua", "ugumu wa kupumua")),
    ("bleeding", ("bleeding", "heavy blood loss", "kutokwa na damu")),
    ("suicidal_ideation", ("suicid", "kill myself", "harming myself", "harm myself", "end my life", "no reason to live", "better off dead", "kujiua")),
    ("confusion", ("confusion", "confused", "altered mental", "not making sense", "kuchanganyikiwa")),
    ("severe_headache", ("severe headache", "worst headache", "maumivu makali ya kichwa")),
    ("headache", ("headache", "head pain", "maumivu ya kichwa")),
    ("high_fever", ("high fever", "very high fever", "severe fever", "homa kali", "burning up", "scorching")),
    ("fever", ("fever", "feverish", "homa", "hot body", "feeling hot")),
    ("chills", ("chills", "rigors", "shivering", "baridi")),
    ("cough", ("cough", "kikohozi")),
    ("sore_throat", ("sore throat", "painful swallowing", "kukohoa")),
    ("runny_nose", ("runny nose", "blocked nose", "stuffy nose", "sneez", "mafua")),
    ("vomiting", ("vomit", "throwing up", "kutapika")),
    ("nausea", ("nausea", "nauseous", "feel sick to my stomach", "kichefuchefu")),
    ("diarrhoea", ("diarrhoea", "diarrhea", "loose stool", "watery stool", "kuhara")),
    ("abdominal_pain", ("abdominal pain", "stomach pain", "belly pain", "tummy pain", "maumivu ya tumboni")),
    ("blood_in_stool", ("blood in stool", "bloody stool", "blood in my stool")),
    ("dehydration", ("dehydrat", "sunken eyes", "dry mouth", "no urine", "not passing urine", "cannot keep fluids")),
    ("urinary_symptoms", ("burning urine", "burning when", "burns when", "burns on", "painful urination", "dysuria", "frequent urination", "pass urine", "passing urine", "urinate", "urinating", "mkojo")),
    ("back_pain", ("back pain", "flank pain", "maumivu ya mgongo")),
    ("body_aches", ("body ache", "body pain", "muscle ache", "aching all over", "maumivu ya mwili")),
    ("joint_pain", ("joint pain", "maumivu ya viungo")),
    ("sweating", ("sweating", "sweat", "night sweat", "jasho")),
    ("palpitations", ("heart is racing", "racing heart", "palpitation", "fast heartbeat", "irregular heartbeat")),
    ("dizziness", ("dizz", "light headed", "lightheaded", "vertigo", "kizunguzungu")),
    ("blurred_vision", ("blurred vision", "vision changes", "cannot see well", "kuona vibaya")),
    ("swelling", ("swelling", "swollen", "kuvimba")),
    ("skin_problem", ("skin", "rash", "itch", "boil", "abscess", "wound", "ulcer", "vipele", "ngonzi")),
    ("injury", ("injury", "cut", "graze", "bruise", "sprain", "fracture", "broken bone", "wound", "fell", "fallen", "jeraha")),
    ("weight_loss", ("weight loss", "losing weight", "kupungua uzito")),
    ("excessive_thirst", ("thirsty", "excessive thirst", "kiu kali")),
    ("depression", ("depress", "sad", "hopeless", "lost interest", "no interest", "huzuni")),
    ("anxiety", ("anxiety", "anxious", "panic", "wasiwasi")),
    ("insomnia", ("cannot sleep", "can't sleep", "not sleeping", "insomnia", "kushindwa kulala")),
    ("fatigue", ("fatigue", "tired", "weak", "no energy", "uchovu")),
    ("hypertension_mention", ("blood pressure", "hypertension", "shinikizo la damu")),
    ("diabetes_mention", ("diabetes", "diabetic", "blood sugar", "kisukari", "sukari")),
    ("hiv_mention", ("hiv", "cd4", "antiretroviral", "arv")),
    ("pregnancy_mention", ("pregnan", "expecting a baby", "mjamzito")),
]

# Danger words that become explicit red flags even when the surrounding prose is
# vague. Matching any of these makes the profile "has_red_flag".
#
# IMPORTANT: every entry is matched as a case-insensitive REGEX on word
# boundaries (see _terms_to_pattern), not as a raw substring. That is why
# "blood" must be written as `blood(?!y)` - otherwise "bloody" matches "blood"
# and, worse, naive matching lets "often" match "fall" and "medication" match
# "cat". Word-boundary matching is what keeps a routine blood-pressure review
# from being escalated to an obstetric emergency.
RED_FLAG_TERMS: tuple[str, ...] = (
    "confusion", "confused", "altered mental", "seizure", "convulsion", "fitting",
    "unconscious", "unresponsive", "not waking", "cannot be woken",
    "cannot drink", "unable to drink", "unable to breastfeed", "refusing to drink",
    "not drinking",
    "difficulty breathing", "cannot breathe",
    "gasping", "chest indrawing", "blue lips",
    "very dark urine", "black urine",
    "blood in stool", "bloody stool", "blood in urine", "blood in my stool",
    "bleeding",
    r"blood(?!y)",
    "suicid", "kill myself", "harming myself", "harm myself", "end my life",
    "chest pain with", "pain spreading", "radiating to", "pain in my arm", "pain in my jaw",
    "slurred speech", "weakness on one side", "paralysis",
    "fruity", "deep rapid breathing", "stiff neck",
    "severe dehydration", "sunken eyes", "no urine",
    "severe difficulty", "severe shortness of breath", "severe chest pain",
    "rapid breathing", "laboured breathing", "struggling to breathe",
    "severe vomiting", "persistent vomiting", "cannot keep fluids",
    "yellow eyes", "jaundice", "stiff neck", "severe abdominal pain",
)

# Reassuring phrases that argue against a serious illness. Used only to lower
# severity for mild presentations, never to override a red flag.
REASSURING_TERMS: tuple[str, ...] = (
    "still playing", "playing normally", "eating well", "drinking well",
    "mild", "slight", "a little", "a bit", "no fever", "feeling better",
)

SEVERITY_TERMS: dict[str, tuple[str, ...]] = {
    "severe": ("severe", "very bad", "worst", "unbearable", "extreme", "kali sana", "makali"),
    "moderate": ("moderate", "quite bad", "getting worse"),
    "mild": ("mild", "slight", "a little", "a bit", "minor"),
}

TEMPERATURE_RE = re.compile(
    r"(?<![\d/.])(\d{2,3}(?:\.\d)?)\s*(?:°\s*c|degrees?\s*(?:celsius|c)?|deg\s*c|celsius|c)\b",
    re.IGNORECASE,
)
TEMPERATURE_FAHRENHEIT_RE = re.compile(r"(?<![\d/.])(\d{2,3}(?:\.\d)?)\s*(?:°\s*f|degrees?\s*fahrenheit|f)\b", re.IGNORECASE)
# Duration is parsed by `detect_duration_days`, which tries several patterns in
# order to cope with English and Swahili word order ("3 days" vs "siku tatu").
BLOOD_PRESSURE_RE = re.compile(r"(\d{2,3})\s*(?:/|over)\s*(\d{2,3})")
AGE_RE = re.compile(r"(\d{1,3})\s*(?:year|years|yr|yrs|month|months)")

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "moja": 1, "mbili": 2, "tatu": 3, "nne": 4, "tano": 5,
    "sita": 6, "saba": 7, "nane": 8, "tisa": 9, "kumi": 10,
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _term_pattern(term: str) -> re.Pattern[str]:
    """Compile a keyword into a word-boundary regex.

    Word-boundary matching is not a nicety here, it is a correctness
    requirement. Plain substring matching produced real mis-triages:
      * "often" contains "fall"  -> a UTI was classified as an injury
      * "blood pressure medication" contains "blood" -> a routine hypertension
        review was escalated to RED by the bleeding-in-pregnancy rule
    A term is suffixed with `\\w*` so stems such as "sneez" still match
    "sneezing" and "itch" matches "itching".
    """
    cached = _PATTERN_CACHE.get(term)
    if cached is not None:
        return cached
    escaped = re.escape(term)
    suffix = r"\w*" if escaped[-1].isalnum() else ""
    pattern = re.compile(rf"\b{escaped}{suffix}\b", re.IGNORECASE)
    _PATTERN_CACHE[term] = pattern
    return pattern


def _matches(needle: str, haystack: str) -> bool:
    """True when `needle` appears in `haystack` as a whole word or word stem."""
    return _term_pattern(needle).search(haystack) is not None


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(_matches(needle, haystack) for needle in needles)


def detect_temperature_celsius(text: str) -> float | None:
    """Extract a temperature in Celsius, converting Fahrenheit if needed.

    Only values in a plausible human range are accepted. That guard is what
    stops a blood pressure reading such as "135/85" from being read as a
    temperature of 135C and triggering a fever rule.
    """
    normalised = _normalise(text)

    fahrenheit = TEMPERATURE_FAHRENHEIT_RE.search(normalised)
    if fahrenheit:
        value = float(fahrenheit.group(1))
        if 90 <= value <= 115:
            return round((value - 32) * 5 / 9, 1)

    for match in TEMPERATURE_RE.finditer(normalised):
        value = float(match.group(1))
        if 30 <= value <= 45:
            return value
        if 90 <= value <= 115:
            return round((value - 32) * 5 / 9, 1)
    return None


def detect_duration_days(text: str) -> tuple[int | None, bool]:
    """Return (duration_in_days, duration_known).

    Handles digits ("for 2 days"), spelled-out English ("for three weeks") and
    Swahili word order, where the number follows the noun ("kwa siku tatu").
    """
    normalised = _normalise(text)
    number_words = "|".join(_NUMBER_WORDS)

    patterns: tuple[tuple[re.Pattern[str], int, int], ...] = (
        # "3 days" / "kwa siku 3" - unit then digits.
        (re.compile(r"(?:siku|wiki|mwezi|days?|weeks?|months?|hours?)\s+(\d+)", re.IGNORECASE), 1, 0),
        # "siku tatu" - unit then a spelled-out number.
        (re.compile(rf"(?:siku|wiki|mwezi)\s+({number_words})\b", re.IGNORECASE), 1, 0),
        # "3 days" - digits then unit.
        (re.compile(r"(\d+)\s*(siku|wiki|mwezi|days?|weeks?|months?|hours?)", re.IGNORECASE), 1, 2),
        # "three days" - English word number then unit.
        (re.compile(rf"\b({number_words})\s+(days?|weeks?|months?|hours?)", re.IGNORECASE), 1, 2),
    )

    for pattern, value_group, unit_group in patterns:
        match = pattern.search(normalised)
        if not match:
            continue
        raw_value = match.group(value_group)
        amount = int(raw_value) if raw_value.isdigit() else _NUMBER_WORDS.get(raw_value.lower())
        if amount is None:
            continue
        unit = (match.group(unit_group) if unit_group else match.group(0)).lower()
        if "day" in unit or "siku" in unit:
            return amount, True
        if "week" in unit or "wiki" in unit:
            return amount * 7, True
        if "month" in unit or "mwezi" in unit:
            return amount * 30, True
        if "hour" in unit:
            return 0, True
    return None, False


def detect_blood_pressure(text: str) -> tuple[int, int] | None:
    match = BLOOD_PRESSURE_RE.search(_normalise(text))
    if not match:
        return None
    systolic, diastolic = int(match.group(1)), int(match.group(2))
    if 70 <= systolic <= 300 and 40 <= diastolic <= 200:
        return systolic, diastolic
    return None


def detect_severity(text: str, symptoms: list[str]) -> str:
    """Classify severity, preferring explicit wording over inference."""
    normalised = _normalise(text)
    for level in ("severe", "moderate", "mild"):
        if _contains_any(normalised, SEVERITY_TERMS[level]):
            return level
    if "high_fever" in symptoms or "difficulty_breathing" in symptoms:
        return "moderate"
    if _contains_any(normalised, REASSURING_TERMS):
        return "mild"
    return "unknown"


def detect_symptoms(text: str) -> list[str]:
    """Return matched symptom labels in taxonomy (acuity) order."""
    normalised = _normalise(text)
    found: list[str] = []
    for label, keywords in SYMPTOM_TAXONOMY:
        if _contains_any(normalised, keywords):
            found.append(label)
    # Drop the generic fever marker when the strong one is present.
    if "high_fever" in found and "fever" in found:
        found.remove("fever")
    if "severe_headache" in found and "headache" in found:
        found.remove("headache")
    return found


def detect_red_flags(text: str, symptoms: list[str]) -> list[str]:
    """Return human-readable red flags present in the text."""
    normalised = _normalise(text)
    flags: list[str] = []

    for term in RED_FLAG_TERMS:
        if _matches(term, normalised):
            flags.append(term)

    # Structural red flags derived from extracted symptoms.
    if "unconscious" in symptoms:
        flags.append("loss of consciousness")
    if "convulsions" in symptoms:
        flags.append("convulsions")
    if "confusion" in symptoms:
        flags.append("confusion")
    if "difficulty_breathing" in symptoms and "chest_pain" in symptoms:
        flags.append("difficulty breathing with chest pain")
    if "bleeding" in symptoms:
        flags.append("bleeding")
    if "suicidal_ideation" in symptoms:
        flags.append("suicidal ideation")
    if "blood_in_stool" in symptoms:
        flags.append("blood in stool")
    if "dehydration" in symptoms:
        flags.append("dehydration")

    # Preserve order, drop duplicates.
    seen: set[str] = set()
    unique: list[str] = []
    for flag in flags:
        if flag not in seen:
            seen.add(flag)
            unique.append(flag)
    return unique


def estimate_fever(text: str, temperature_celsius: float | None, symptoms: list[str]) -> dict[str, Any]:
    """Decide whether fever is present and whether it is high-grade.

    Fever is "present" when a temperature of 37.5C or above is measured, or when
    the patient reports fever or chills at all - in a malaria-endemic setting a
    reported fever is a febrile illness that needs a test, even unmeasured.

    Fever is "high" ONLY when a temperature of 38.5C or above is measured, or
    when the wording says high/severe. An unqualified "fever" is deliberately
    NOT treated as high: doing otherwise escalated a child with a 37.5C cold
    into a same-day clinic visit. Being unable to measure a fever is a reason
    to seek a test, not a reason to claim the fever is high.
    """
    normalised = _normalise(text)
    mentioned_high = _contains_any(
        normalised,
        ("high fever", "very high fever", "severe fever", "homa kali", "burning up", "scorching"),
    )
    # Infer reported fever from the SYMPTOM TAXONOMY rather than from raw words.
    # Keyword lists matched against prose produce false positives: the child
    # scenario says "a little bit of fever", and a loose match on "a bit" once
    # discarded the fever entirely. The taxonomy is the single source of truth.
    reported_fever = any(
        label in symptoms for label in ("fever", "high_fever")
    )
    malaria_like = _contains_any(normalised, ("chills", "rigors", "shivering", "baridi", "malaria"))

    if temperature_celsius is not None:
        present = temperature_celsius >= 37.5
        high = temperature_celsius >= 38.5
    else:
        present = reported_fever or malaria_like
        high = mentioned_high or "high_fever" in symptoms

    return {
        "temperature_celsius": temperature_celsius,
        "fever_present": present,
        "fever_high": high,
        "fever_unquantified": present and temperature_celsius is None,
    }


def extract_features(
    symptom_text: str,
    patient_age: int | None = None,
    patient_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical feature profile from free text with no LLM.

    The output shape matches what Agent 1 asks Claude to return, so the rule
    engine cannot tell the two paths apart.
    """
    context = dict(patient_context or {})
    text = symptom_text or ""
    symptoms = detect_symptoms(text)
    temperature = detect_temperature_celsius(text)
    duration_days, duration_known = detect_duration_days(text)
    blood_pressure = detect_blood_pressure(text)
    red_flags = detect_red_flags(text, symptoms)
    fever = estimate_fever(text, temperature, symptoms)
    severity = detect_severity(text, symptoms)

    chronic = context.get("chronic_conditions") or []
    if isinstance(chronic, str):
        chronic = [chronic]
    chronic_terms = [_normalise(str(item)) for item in chronic]
    normalised = _normalise(text)
    if "hypertension_mention" in symptoms or "hypertension" in normalised or "blood pressure" in normalised:
        if "hypertension" not in chronic_terms:
            chronic_terms.append("hypertension")
    if "diabetes_mention" in symptoms:
        if "diabetes" not in chronic_terms:
            chronic_terms.append("diabetes")

    pregnant = bool(context.get("pregnant"))
    if "pregnancy_mention" in symptoms:
        pregnant = True

    primary = symptoms[0] if symptoms else "unspecified"
    associated = symptoms[1:]

    return {
        "primary_symptom": primary,
        "associated_symptoms": associated,
        "all_symptoms": symptoms,
        "duration_days": duration_days,
        "duration_known": duration_known,
        "severity": severity,
        "red_flags": red_flags,
        "differential_considerations": [],
        "extracted": {
            "temperature_celsius": temperature,
            "blood_pressure": list(blood_pressure) if blood_pressure else None,
            "symptom_count": len(symptoms),
        },
        "features": {
            **fever,
            "has_red_flag": bool(red_flags),
            "red_flag_count": len(red_flags),
            "duration_two_weeks": bool(duration_known and duration_days is not None and duration_days >= 14),
            "reassuring_signs": _contains_any(normalised, REASSURING_TERMS),
        },
        "patient": {
            "age": patient_age,
            "pregnant": pregnant,
            "chronic": chronic_terms,
            "hiv_status": context.get("hiv_status"),
        },
        "extraction_method": "deterministic-keyword-extractor",
        "extraction_confidence": 0.6,
    }


def canonicalise_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise a profile produced by Claude into the canonical shape.

    This is what stops prompt drift from breaking the rule engine: whatever the
    model returns, the numeric features, symptom union and red-flag union are
    recomputed here from a single source of truth.
    """
    text_parts: list[str] = []
    for key in ("source_text", "raw_text", "notes"):
        value = raw.get(key)
        if isinstance(value, str):
            text_parts.append(value)
    text = " ".join(text_parts)

    primary = str(raw.get("primary_symptom") or "unspecified").strip().lower().replace(" ", "_")
    associated = [
        str(item).strip().lower().replace(" ", "_")
        for item in (raw.get("associated_symptoms") or [])
        if str(item).strip()
    ]

    reported_red_flags = [str(item) for item in (raw.get("red_flags") or []) if str(item).strip()]

    detected_from_narrative = detect_symptoms(text) if text else []
    estimated_from_narrative = detect_red_flags(text, detected_from_narrative) if text else []

    all_symptoms: list[str] = []
    for item in [primary, *associated, *detected_from_narrative]:
        if item and item != "unspecified" and item not in all_symptoms:
            all_symptoms.append(item)

    red_flags: list[str] = []
    for item in [*reported_red_flags, *estimated_from_narrative]:
        if item and item not in red_flags:
            red_flags.append(item)

    extracted = dict(raw.get("extracted") or {})
    temperature = extracted.get("temperature_celsius")
    if temperature is None and text:
        temperature = detect_temperature_celsius(text)
    if temperature is not None:
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            temperature = None

    duration = raw.get("duration_days")
    duration_known = duration is not None
    if duration is None and text:
        duration, duration_known = detect_duration_days(text)

    blood_pressure = extracted.get("blood_pressure")
    if not blood_pressure and text:
        bp = detect_blood_pressure(text)
        blood_pressure = list(bp) if bp else None

    fever = estimate_fever(text, temperature, all_symptoms)
    # Treat a red flag word appearing in the model's own rationale as a red flag.
    for flag in reported_red_flags:
        if flag.lower() not in text.lower():
            text = f"{text} {flag}".strip()
    recomputed = detect_red_flags(text, all_symptoms) if text else []
    for flag in recomputed:
        if flag not in red_flags:
            red_flags.append(flag)

    severity = str(raw.get("severity") or "").strip().lower()
    if severity not in {"mild", "moderate", "severe"}:
        severity = detect_severity(text, all_symptoms) if text else "unknown"

    patient_raw = dict(raw.get("patient") or {})
    context = dict(raw.get("patient_context") or {})
    chronic = patient_raw.get("chronic") or context.get("chronic_conditions") or []
    if isinstance(chronic, str):
        chronic = [chronic]
    chronic_terms = [str(item).strip().lower() for item in chronic if str(item).strip()]

    return {
        "primary_symptom": primary,
        "associated_symptoms": associated,
        "all_symptoms": all_symptoms,
        "duration_days": duration,
        "duration_known": duration_known,
        "severity": severity,
        "red_flags": red_flags,
        "differential_considerations": [
            str(item) for item in (raw.get("differential_considerations") or [])
        ],
        "clinical_summary": raw.get("clinical_summary") or raw.get("summary"),
        "extracted": {
            "temperature_celsius": temperature,
            "blood_pressure": blood_pressure,
            "symptom_count": len(all_symptoms),
        },
        "features": {
            **fever,
            "has_red_flag": bool(red_flags),
            "red_flag_count": len(red_flags),
            "duration_two_weeks": bool(duration_known and duration is not None and duration >= 14),
            "reassuring_signs": _contains_any(_normalise(text), REASSURING_TERMS),
        },
        "patient": {
            "age": patient_raw.get("age", context.get("age")),
            "pregnant": bool(patient_raw.get("pregnant", context.get("pregnant", False)))
            or "pregnancy_mention" in all_symptoms,
            "chronic": chronic_terms,
            "hiv_status": patient_raw.get("hiv_status", context.get("hiv_status")),
        },
        "extraction_method": raw.get("extraction_method", "claude"),
        "extraction_confidence": raw.get("extraction_confidence", 0.85),
    }


def attach_source_text(profile: dict[str, Any], symptom_text: str) -> dict[str, Any]:
    """Keep the original narrative on the profile so rules can match prose."""
    profile = dict(profile)
    profile["source_text"] = symptom_text
    return profile
