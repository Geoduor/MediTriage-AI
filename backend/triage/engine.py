"""Deterministic triage rule engine.

Person 1 (Lead Developer + DevOps) owns this file.
Person 3 (Data & Content Specialist) owns the rules it evaluates.

Design rule: **this module has no LLM dependency and never will.** Triage level
is decided here by evaluating `backend/data/triage_rules.json` in priority
order. Agent 1 may enrich the feature profile with Claude, but a model outage
must never change whether a patient is told RED, YELLOW or GREEN - it may only
change how nicely the advice is worded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

# Canonical level metadata. Kept in code because it is presentation contract,
# not clinical content.
LEVEL_META: dict[str, dict[str, str]] = {
    "RED": {
        "urgency": "EMERGENCY",
        "colour": "#d32f2f",
        "label_en": "EMERGENCY - go to hospital now",
        "label_sw": "HATARI - nenda hospitalini sasa",
        "target_time": "immediately",
    },
    "YELLOW": {
        "urgency": "URGENT",
        "colour": "#f9a825",
        "label_en": "URGENT - go to the clinic today",
        "label_sw": "HARAKA - nenda kliniki leo",
        "target_time": "within 24 hours",
    },
    "GREEN": {
        "urgency": "ROUTINE",
        "colour": "#2e7d32",
        "label_en": "ROUTINE - manage at home, review if worse",
        "label_sw": "KAWAIDA - jitunze nyumbani, rudi ikiwa inazidi",
        "target_time": "no time pressure",
    },
}


class RuleEngineError(RuntimeError):
    """Raised when a rule references an unknown field or operator."""


@dataclass
class RuleMatch:
    """The outcome of evaluating the rule set."""

    triage_level: str
    urgency: str
    rationale: str
    recommended_pathway: str
    sha_fund: str | None
    rule_id: str
    rule_name: str
    colour: str = ""
    label_en: str = ""
    label_sw: str = ""
    target_time: str = ""
    alternatives: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "triage_level": self.triage_level,
            "urgency": self.urgency,
            "rationale": self.rationale,
            "recommended_pathway": self.recommended_pathway,
            "sha_fund": self.sha_fund,
            "matched_rule": {"rule_id": self.rule_id, "name": self.rule_name},
            "colour": self.colour,
            "label_en": self.label_en,
            "label_sw": self.label_sw,
            "target_time": self.target_time,
            "engine": "deterministic-rules-v1",
            "alternatives": self.alternatives,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
# Rules address the *canonical* profile, not the extractor's internal layout.
# Keeping the translation here means Person 3 can write natural paths such as
# `symptoms.all` without knowing how the extractor stores things.
#
# Each alias maps to a tuple of PATHS, and each path is itself a tuple of keys.
# A field with one path resolves to that value; a field with several paths
# resolves to their merged text, which lets rules match against the raw
# narrative as well as the extracted symptoms.
_PATH_ALIASES: dict[str, tuple[tuple[str, ...], ...]] = {
    "symptoms.primary": (("primary_symptom",),),
    "symptoms.associated": (("associated_symptoms",),),
    "symptoms.all": (
        ("all_symptoms",),
        ("source_text",),
        ("primary_symptom",),
        ("associated_symptoms",),
    ),
    # Labels only - no raw narrative. Prefer this for rules whose second
    # condition is a generic English word. Matching generic words against prose
    # caused a urinary tract infection to match the injury rule because the
    # patient's sentence contained "severe", and a UTI to be escalated to
    # YELLOW by a wound-care rule.
    "symptoms.labels": (
        ("all_symptoms",),
        ("primary_symptom",),
        ("associated_symptoms",),
    ),
    "features.fever_present": (("features", "fever_present"),),
    "features.fever_high": (("features", "fever_high"),),
    "features.has_red_flag": (("features", "has_red_flag"),),
    "features.duration_two_weeks": (("features", "duration_two_weeks"),),
    "patient.pregnant": (("patient", "pregnant"),),
    "patient.chronic": (("patient", "chronic"),),
    "patient.age": (("patient", "age"),),
    "severity": (("severity",),),
    "duration_days": (("duration_days",),),
    "red_flags": (("red_flags",),),
}


def _walk(profile: dict[str, Any], parts: tuple[str, ...]) -> Any:
    """Follow a nested key path, returning None if any step is missing."""
    current: Any = profile
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def resolve_path(profile: dict[str, Any], path: str) -> Any:
    """Resolve a rule field path against a canonical profile.

    Reading the alias parts as top-level keys (rather than as a nested path)
    made `features.fever_high` resolve to the whole `features` dict, which is
    truthy, so `{"field": "features.fever_high", "eq": true}` matched every
    patient and escalated the entire demo to YELLOW.
    """
    if path in _PATH_ALIASES:
        values = [
            value
            for value in (_walk(profile, candidate) for candidate in _PATH_ALIASES[path])
            if value not in (None, "", [], {})
        ]
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        merged: list[str] = []
        for value in values:
            if isinstance(value, (list, tuple, set)):
                merged.extend(str(item) for item in value)
            else:
                merged.append(str(value))
        return merged

    return _walk(profile, tuple(path.split(".")))


# ---------------------------------------------------------------------------
# Predicate evaluation
# ---------------------------------------------------------------------------
def _as_text_list(value: Any) -> list[str]:
    """Flatten a profile value into lowercase, space-separated strings.

    Underscores become spaces because symptom labels are stored in snake_case
    ("chest_pain") while rules are written in prose ("chest pain"). Without this
    normalisation the two can never match, and a cardiac emergency silently
    fell through to the routine default rule.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value.lower().replace("_", " ")]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            if isinstance(item, (list, tuple, set)):
                out.extend(str(entry).lower().replace("_", " ") for entry in item)
            else:
                out.append(str(item).lower().replace("_", " "))
        return out
    if isinstance(value, bool):
        return ["true" if value else "false"]
    return [str(value).lower().replace("_", " ")]


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _matches_any(value: Any, needles: Iterable[str]) -> bool:
    """True when any needle appears in the (normalised) value."""
    haystack = " | ".join(_as_text_list(value))
    return any(str(needle).lower().replace("_", " ") in haystack for needle in needles)


def evaluate_predicate(profile: dict[str, Any], predicate: dict[str, Any]) -> bool:
    """Evaluate one predicate against the profile."""
    field_path = predicate.get("field")
    if not field_path:
        raise RuleEngineError(f"Predicate is missing 'field': {predicate!r}")

    value = resolve_path(profile, field_path)

    if not any(key in predicate for key in ("any", "all", "none", "eq", "not_eq", "lt", "lte", "gt", "gte", "exists")):
        raise RuleEngineError(f"Predicate has no operator: {predicate!r}")

    if "exists" in predicate:
        wants_present = bool(predicate["exists"])
        is_present = value not in (None, "", [], {})
        if wants_present != is_present:
            return False

    if "any" in predicate and not _matches_any(value, predicate["any"]):
        return False

    if "all" in predicate:
        haystack = " | ".join(_as_text_list(value))
        if not all(str(needle).lower() in haystack for needle in predicate["all"]):
            return False

    if "none" in predicate and _matches_any(value, predicate["none"]):
        return False

    if "eq" in predicate:
        expected = predicate["eq"]
        if isinstance(expected, bool):
            if bool(value) is not expected:
                return False
        elif str(value).lower() != str(expected).lower():
            return False

    if "not_eq" in predicate and str(value).lower() == str(predicate["not_eq"]).lower():
        return False

    for operator, comparator in (("lt", lambda a, b: a < b), ("lte", lambda a, b: a <= b),
                                 ("gt", lambda a, b: a > b), ("gte", lambda a, b: a >= b)):
        if operator in predicate:
            actual = _as_number(value)
            if actual is None or not comparator(actual, float(predicate[operator])):
                return False

    return True


def rule_matches(profile: dict[str, Any], rule: dict[str, Any]) -> bool:
    """A rule matches when every predicate matches (logical AND)."""
    return all(evaluate_predicate(profile, predicate) for predicate in rule.get("predicates", []))


def _build_match(profile: dict[str, Any], rule: dict[str, Any], default_level: str) -> RuleMatch:
    level = rule.get("triage_level", default_level)
    meta = LEVEL_META[level]
    return RuleMatch(
        triage_level=level,
        urgency=rule.get("urgency", meta["urgency"]),
        rationale=rule.get("rationale", ""),
        recommended_pathway=rule.get("recommended_pathway", "clinic"),
        sha_fund=rule.get("sha_fund"),
        rule_id=rule.get("rule_id", "unknown"),
        rule_name=rule.get("name", "unnamed rule"),
        colour=meta["colour"],
        label_en=meta["label_en"],
        label_sw=meta["label_sw"],
        target_time=meta["target_time"],
        confidence=float(profile.get("extraction_confidence", 1.0)),
    )


def triage(profile: dict[str, Any], rules: list[dict[str, Any]], rules_meta: dict[str, Any] | None = None) -> RuleMatch:
    """Evaluate the ordered rule set and return the first match.

    Rules are assumed pre-sorted by priority (the loader guarantees this).
    """
    meta = rules_meta or {}
    default_level = meta.get("evaluation", {}).get("default_level", "GREEN")

    for rule in rules:
        if rule_matches(profile, rule):
            match = _build_match(profile, rule, default_level)
            # Surface the next-best candidates for clinical review and debugging.
            match.alternatives = _alternatives(profile, rules, rule.get("rule_id"))
            return match

    return RuleMatch(
        triage_level=default_level,
        urgency=LEVEL_META[default_level]["urgency"],
        rationale="No rule matched the extracted features. Defaulted to routine care.",
        recommended_pathway="clinic",
        sha_fund="PHF",
        rule_id="fallback",
        rule_name="Engine fallback",
        colour=LEVEL_META[default_level]["colour"],
        label_en=LEVEL_META[default_level]["label_en"],
        label_sw=LEVEL_META[default_level]["label_sw"],
        target_time=LEVEL_META[default_level]["target_time"],
        confidence=0.3,
    )


def _alternatives(profile: dict[str, Any], rules: list[dict[str, Any]], matched_id: str | None) -> list[dict[str, str]]:
    """Return up to two other matching rules, for auditability."""
    out: list[dict[str, str]] = []
    for rule in rules:
        if rule.get("rule_id") == matched_id:
            continue
        if rule_matches(profile, rule):
            out.append(
                {
                    "rule_id": str(rule.get("rule_id")),
                    "name": str(rule.get("name")),
                    "triage_level": str(rule.get("triage_level")),
                }
            )
        if len(out) >= 2:
            break
    return out


def referenced_fields(rules: list[dict[str, Any]]) -> set[str]:
    """Every field path the rule set depends on. Used by the test suite."""
    fields: set[str] = set()
    for rule in rules:
        for predicate in rule.get("predicates", []):
            if predicate.get("field"):
                fields.add(str(predicate["field"]))
    return fields


def known_field_paths() -> set[str]:
    """Field paths the engine is able to resolve."""
    return set(_PATH_ALIASES)


def unknown_referenced_fields(rules: list[dict[str, Any]]) -> set[str]:
    """Rule fields the engine cannot resolve - a content bug, caught by tests."""
    return referenced_fields(rules) - known_field_paths()
