"""Regression tests for bugs found while building the deterministic engine.

Every test in this file corresponds to a defect that produced a WRONG TRIAGE
LEVEL, not a cosmetic problem. They exist so the same class of bug cannot return
unnoticed - a mis-triage is the most expensive failure this system can have.

Found by running `python verify.py` and `python debug_case.py`.
"""
from __future__ import annotations

import pytest

from knowledge.loader import load_knowledge_base
from orchestrator import run_full_triage
from triage.engine import _as_text_list, evaluate_predicate, resolve_path, rule_matches, triage
from triage.extractor import detect_symptoms, detect_temperature_celsius, extract_features


def resolved_text(profile: dict, path: str) -> str:
    """Render a resolved path the way the engine compares it."""
    return " | ".join(_as_text_list(resolve_path(profile, path)))


def _triage(symptoms: str, age: int | None = None, context: dict | None = None, kb=None):
    kb = kb or load_knowledge_base()
    return run_full_triage(
        symptoms=symptoms,
        patient_age=age,
        patient_context=context or {},
        knowledge_base=kb,
        use_llm=False,
    ).to_dict()


class TestBugUnderscoreLabelsNeverMatchedRules:
    """BUG 1 - symptom labels are snake_case, rule keywords are prose.

    `chest_pain` could never match the keyword `chest pain`, so the cardiac
    emergency rule failed to fire and a suspected heart attack was triaged
    GREEN. `_as_text_list` now converts underscores to spaces.
    """

    def test_underscore_labels_resolve_to_spaced_text(self):
        """`resolve_path` returns raw values; `_as_text_list` does the normalising.

        The assertion therefore goes through `evaluate_predicate`, which is the
        path the rule engine actually uses.
        """
        profile = {"all_symptoms": ["chest_pain", "difficulty_breathing"]}
        assert resolved_text(profile, "symptoms.all") == "chest pain | difficulty breathing"
        assert evaluate_predicate(profile, {"field": "symptoms.all", "any": ["chest pain"]})
        assert evaluate_predicate(profile, {"field": "symptoms.all", "any": ["difficulty breathing"]})

    def test_prose_keyword_matches_snake_case_label(self):
        profile = {"all_symptoms": ["chest_pain"]}
        assert evaluate_predicate(profile, {"field": "symptoms.all", "any": ["chest pain"]})

    def test_cardiac_emergency_is_red(self):
        result = _triage(
            "I have severe chest pain, it feels like pressure, and I am having "
            "trouble breathing. I am sweating and my heart is racing.",
            age=52,
        )
        assert result["triage"]["triage_level"] == "RED"
        assert result["triage"]["matched_rule"]["rule_id"] == "r001"
        assert result["triage"]["sha_fund"] == "ECCIF"


class TestBugNestedAliasReadAsTopLevelKeys:
    """BUG 2 - alias tuples were read as top-level keys.

    `features.fever_high` resolved to the whole `features` dict, which is
    truthy, so `{"field": "features.fever_high", "eq": true}` matched EVERY
    patient and escalated the entire demo to YELLOW.
    """

    def test_nested_feature_resolves_to_scalar(self):
        profile = {"features": {"fever_high": False, "fever_present": True}}
        assert resolve_path(profile, "features.fever_high") is False
        assert resolve_path(profile, "features.fever_present") is True

    def test_false_feature_does_not_satisfy_eq_true(self):
        profile = {"features": {"fever_high": False}}
        assert not evaluate_predicate(profile, {"field": "features.fever_high", "eq": True})

    def test_missing_feature_is_not_truthy(self):
        assert resolve_path({}, "features.fever_high") is None
        assert not evaluate_predicate({}, {"field": "features.fever_high", "eq": True})

    def test_routine_hypertension_is_green_not_red(self):
        """The end-to-end symptom of this bug: everyone became YELLOW."""
        result = _triage(
            "My blood pressure monitor at home shows 135/85. I am on blood "
            "pressure medication but want to check if I am doing well.",
            age=55,
            context={"chronic_conditions": ["hypertension"]},
        )
        assert result["triage"]["triage_level"] == "GREEN"
        assert result["triage"]["sha_fund"] == "PHF"


class TestBugSubstringMatchingCausedFalsePositives:
    """BUG 3 - keywords were matched as raw substrings.

    "often" contains "fall", so "I go very often" was classified as an INJURY and
    escalated to YELLOW. Matching is now word-boundary based.
    """

    def test_fall_does_not_match_inside_often(self):
        assert "injury" not in detect_symptoms("I go very often")

    def test_bite_does_not_match_inside_words(self):
        assert "injury" not in detect_symptoms("It burns when I pass urine")

    def test_real_fall_is_still_detected(self):
        assert "injury" in detect_symptoms("I fell and hurt my knee")

    def test_uncomplicated_uti_is_green(self):
        result = _triage("It burns when I pass urine and I go very often.", age=24)
        assert result["triage"]["triage_level"] == "GREEN"


class TestBugBloodPressureReadAsTemperature:
    """BUG 4 - "135/85" was parsed as a temperature, creating a false fever."""

    def test_blood_pressure_is_not_a_temperature(self):
        assert detect_temperature_celsius("My blood pressure is 135/85") is None

    def test_fahrenheit_still_converts(self):
        assert detect_temperature_celsius("fever of 102 F") == pytest.approx(38.9, abs=0.1)

    def test_celsius_forms_are_recognised(self):
        assert detect_temperature_celsius("temperature is 38.5C") == pytest.approx(38.5)
        assert detect_temperature_celsius("temp 37.5 degrees") == pytest.approx(37.5)
        assert detect_temperature_celsius("39.2 degrees celsius") == pytest.approx(39.2)


class TestBugUnquantifiedFeverTreatedAsHigh:
    """BUG 5 - an unqualified "fever" was treated as a HIGH fever.

    That pushed a child with a 37.5C cold into a same-day clinic visit, and made
    every unmeasured fever match the high-fever rules. Being unable to measure a
    fever is a reason to seek a test, not a reason to claim it is high.
    """

    def test_low_grade_fever_is_present_but_not_high(self):
        profile = extract_features("fever at 37.5 degrees", None, {})
        assert profile["features"]["fever_present"] is True
        assert profile["features"]["fever_high"] is False

    def test_unqualified_fever_is_not_high(self):
        profile = extract_features("I have had a fever since yesterday")
        assert profile["features"]["fever_present"] is True
        assert profile["features"]["fever_high"] is False

    def test_explicit_high_fever_is_high(self):
        assert extract_features("I have a very high fever")["features"]["fever_high"] is True

    def test_measured_high_fever_is_high(self):
        assert extract_features("temperature 39.5C")["features"]["fever_high"] is True

    def test_child_with_cold_is_green(self):
        result = _triage(
            "My child has a runny nose, mild cough, and a little bit of fever at "
            "37.5 degrees. He is still playing but a bit tired.",
            age=8,
        )
        assert result["triage"]["triage_level"] == "GREEN"
        assert result["triage"]["sha_fund"] == "PHF"


class TestBugGenericKeywordsMatchedNarrative:
    """BUG 6 - generic words in keyword lists matched the raw narrative.

    The injury rule's keyword list contained "severe". A UTI whose sentence
    happened to contain "severe" was escalated to YELLOW by a wound-care rule.
    Rules now match a label-only alias for that condition.
    """

    def test_labels_alias_excludes_raw_narrative(self):
        profile = {
            "all_symptoms": ["urinary_symptoms"],
            "source_text": "severe pain, dirty feeling",
            "primary_symptom": "urinary_symptoms",
            "associated_symptoms": [],
        }
        labels = " | ".join(resolve_path(profile, "symptoms.labels"))
        assert "severe" not in labels
        assert "dirty" not in labels

    def test_uti_does_not_match_the_injury_rule(self, ):
        kb = load_knowledge_base()
        profile = extract_features("It burns when I pass urine and I go very often.", 24, {})
        injury_rule = next(r for r in kb.rules if r["rule_id"] == "r111")
        assert not rule_matches(profile, injury_rule)

    def test_uti_does_not_match_the_skin_rule(self):
        kb = load_knowledge_base()
        profile = extract_features("It burns when I pass urine and I go very often.", 24, {})
        skin_rule = next(r for r in kb.rules if r["rule_id"] == "r110")
        assert not rule_matches(profile, skin_rule)


class TestBugClinicallyUnsafeDefault:
    """BUG 7 - the engine defaulted to GREEN, the unsafe direction.

    The default level stays GREEN (most presentations are routine), but an
    unanalysable profile must never reach it. This test pins that behaviour.
    """

    def test_empty_profile_hits_default_rule(self):
        kb = load_knowledge_base()
        match = triage({}, kb.rules, kb.rule_meta)
        assert match.rule_id == "r999"
        assert match.triage_level == "GREEN"

    def test_unanalysable_profile_is_floored_at_yellow(self, monkeypatch):
        import orchestrator

        def exploding_analyzer(*args, **kwargs):
            raise RuntimeError("simulated extractor failure")

        monkeypatch.setattr(orchestrator, "analyze_symptoms", exploding_analyzer)
        outcome = orchestrator.run_full_triage(
            symptoms="something unreadable",
            patient_age=40,
            use_llm=False,
        ).to_dict()
        assert outcome["triage"]["triage_level"] in {"YELLOW", "RED"}
        assert "agent_1:RuntimeError" in outcome["audit"]["degraded_components"]


class TestAllFiveScenariosOneMoreTime:
    """A final guard: the demo contract, asserted in one place."""

    @pytest.mark.parametrize(
        "index,expected",
        [(0, "YELLOW"), (1, "GREEN"), (2, "RED"), (3, "RED"), (4, "GREEN")],
    )
    def test_scenario(self, index, expected):
        case = load_knowledge_base().test_cases[index]
        result = _triage(
            case["symptoms"],
            age=case.get("patient_age"),
            context=case.get("patient_context") or {},
        )
        assert result["triage"]["triage_level"] == expected
