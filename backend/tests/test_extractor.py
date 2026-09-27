"""Tests for the deterministic feature extractor.

These tests are what make the offline path trustworthy. If they pass, the demo
works with no API key.
"""
from __future__ import annotations

import pytest

from triage.extractor import (
    canonicalise_profile,
    detect_blood_pressure,
    detect_duration_days,
    detect_red_flags,
    detect_symptoms,
    detect_temperature_celsius,
    estimate_fever,
    extract_features,
)


class TestTemperature:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("fever at 39.2 degrees celsius", 39.2),
            ("temperature is 38.5C", 38.5),
            ("temp 37.5 c", 37.5),
            ("fever of 102 F", 38.9),
            ("no temperature mentioned", None),
        ],
    )
    def test_detects_celsius(self, text, expected):
        result = detect_temperature_celsius(text)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected, abs=0.1)

    def test_ignores_implausible_values(self):
        assert detect_temperature_celsius("BP 120/80 and pulse 72") is None


class TestDuration:
    @pytest.mark.parametrize(
        "text,expected_days",
        [
            ("fever for 2 days", 2),
            ("cough for three weeks", 21),
            ("symptoms for 1 week", 7),
            ("been unwell for 1 month", 30),
            ("Nina homa kwa siku tatu", 3),
            ("no duration", None),
        ],
    )
    def test_detects_duration(self, text, expected_days):
        days, known = detect_duration_days(text)
        if expected_days is None:
            assert not known
        else:
            assert days == expected_days
            assert known

    def test_flags_two_week_threshold(self):
        profile = extract_features("I have had a cough for three weeks.")
        assert profile["features"]["duration_two_weeks"] is True

    def test_short_duration_is_not_two_weeks(self):
        profile = extract_features("I have had a cough for 3 days.")
        assert profile["features"]["duration_two_weeks"] is False


class TestBloodPressure:
    def test_reads_slash_format(self):
        assert detect_blood_pressure("My blood pressure is 135/85") == (135, 85)

    def test_reads_over_format(self):
        assert detect_blood_pressure("BP 180 over 110") == (180, 110)

    def test_absent(self):
        assert detect_blood_pressure("I have a headache") is None


class TestSymptoms:
    def test_english(self):
        found = detect_symptoms("I have fever, headache and body aches")
        assert "fever" in found
        assert "headache" in found
        assert "body_aches" in found

    def test_swahili(self):
        found = detect_symptoms("Nina homa kali, maumivu ya kichwa na kikohozi")
        assert "high_fever" in found
        assert "headache" in found
        assert "cough" in found

    def test_acute_symptom_becomes_primary(self):
        profile = extract_features("I have a cough and also severe chest pain with trouble breathing")
        assert profile["primary_symptom"] == "chest_pain"

    def test_collapses_generic_fever_when_high(self):
        found = detect_symptoms("I have a very high fever")
        assert "high_fever" in found
        assert "fever" not in found


class TestRedFlags:
    def test_detects_suicidal_ideation(self):
        flags = detect_red_flags("I keep thinking about harming myself", ["suicidal_ideation"])
        assert any("suicid" in flag for flag in flags)

    def test_detects_convulsions(self):
        flags = detect_red_flags("he had a seizure last night", ["convulsions"])
        assert flags

    def test_detects_bleeding(self):
        flags = detect_red_flags("I started bleeding", ["bleeding"])
        assert flags

    def test_clean_case_has_no_red_flags(self):
        profile = extract_features("I have a runny nose and a mild cough")
        assert profile["features"]["has_red_flag"] is False

    def test_does_not_invent_flags(self):
        profile = extract_features("My blood pressure is 135/85 and I feel fine")
        assert profile["red_flags"] == []


class TestFeverEstimation:
    def test_high_fever_by_temperature(self):
        fever = estimate_fever("temp 39", 39.0, [])
        assert fever["fever_present"] and fever["fever_high"]

    def test_low_grade_fever_is_present_but_not_high(self):
        fever = estimate_fever("fever at 37.5 degrees", 37.5, [])
        assert fever["fever_present"] is True
        assert fever["fever_high"] is False

    def test_no_fever(self):
        fever = estimate_fever("I have a runny nose", None, [])
        assert fever["fever_present"] is False

    def test_qualitative_high_fever(self):
        fever = estimate_fever("I have a very high fever", None, ["high_fever"])
        assert fever["fever_high"] is True

    def test_chills_imply_febrile_illness(self):
        fever = estimate_fever("I have chills and body aches", None, ["chills"])
        assert fever["fever_present"] is True

    def test_fahrenheit_conversion(self):
        assert detect_temperature_celsius("fever 102 F") == pytest.approx(38.9, abs=0.1)


class TestPatientContext:
    def test_pregnancy_from_context(self):
        profile = extract_features("I have a headache", patient_context={"pregnant": True})
        assert profile["patient"]["pregnant"] is True

    def test_pregnancy_from_text(self):
        profile = extract_features("I am 7 months pregnant and bleeding")
        assert profile["patient"]["pregnant"] is True

    def test_chronic_conditions_preserved(self):
        profile = extract_features(
            "My blood pressure reading is 135/85",
            patient_context={"chronic_conditions": ["hypertension"]},
        )
        assert "hypertension" in profile["patient"]["chronic"]

    def test_diabetes_inferred_from_text(self):
        profile = extract_features("I am diabetic and my sugar is high")
        assert "diabetes" in profile["patient"]["chronic"]


class TestCanonicalisation:
    """The canonicaliser is the guard against LLM prompt drift."""

    def test_recomputes_features_from_source_text(self):
        raw = {
            "primary_symptom": "chest pain",
            "associated_symptoms": ["sweating"],
            "source_text": "severe chest pain, trouble breathing, sweating, heart is racing",
            "severity": "severe",
        }
        profile = canonicalise_profile(raw)
        assert profile["features"]["has_red_flag"] is True
        assert "difficulty_breathing" in profile["all_symptoms"]

    def test_unions_model_symptoms_with_keyword_scan(self):
        raw = {
            "primary_symptom": "fever",
            "associated_symptoms": [],
            "source_text": "fever and a bad cough for two weeks",
        }
        profile = canonicalise_profile(raw)
        assert "cough" in profile["all_symptoms"]
        assert profile["features"]["duration_two_weeks"] is True

    def test_invalid_severity_is_recovered_or_defaulted(self):
        raw = {"primary_symptom": "cough", "severity": "extremely bad", "source_text": "a mild cough"}
        profile = canonicalise_profile(raw)
        assert profile["severity"] in {"mild", "moderate", "severe", "unknown"}

    def test_handles_empty_profile(self):
        profile = canonicalise_profile({})
        assert profile["primary_symptom"] == "unspecified"
        assert profile["features"]["has_red_flag"] is False
