"""The demo contract: all 5 hackathon scenarios must triage as documented.

This is the single most important test file in the repository. It is what stops
a prompt edit, a rule edit or a refactor from silently changing a patient-facing
urgency level.

Run:
    cd backend
    python -m pytest tests/test_scenarios.py -v
"""
from __future__ import annotations

import pytest

from orchestrator import run_full_triage
from triage.engine import unknown_referenced_fields


def _triage(case: dict, knowledge_base):
    context = dict(case.get("patient_context") or {})
    if case.get("location") and "location" not in context:
        context["location"] = case["location"]
    outcome = run_full_triage(
        symptoms=case["symptoms"],
        patient_age=case.get("patient_age"),
        patient_context=context,
        language=case.get("language", "en"),
        sex=case.get("sex"),
        knowledge_base=knowledge_base,
        use_llm=False,
    )
    return outcome.to_dict()


@pytest.mark.parametrize("index", range(5))
def test_demo_scenario_triage_level(index, demo_cases, knowledge_base):
    """Each demo scenario returns the documented RED / YELLOW / GREEN level."""
    case = demo_cases[index]
    payload = _triage(case, knowledge_base)
    actual = payload["triage"]["triage_level"]
    assert actual == case["expected_triage_level"], (
        f"Scenario {case['scenario_id']} ({case['patient_name']}) returned {actual}, "
        f"expected {case['expected_triage_level']}.\n"
        f"Matched rule: {payload['triage']['matched_rule']}\n"
        f"Rationale: {payload['triage']['rationale']}\n"
        f"Extracted symptoms: {payload['symptom_analysis']['all_symptoms']}\n"
        f"Red flags: {payload['symptom_analysis']['red_flags']}"
    )


@pytest.mark.parametrize("index", range(5))
def test_demo_scenario_pathway(index, demo_cases, knowledge_base):
    """Each scenario routes to the documented care pathway."""
    case = demo_cases[index]
    payload = _triage(case, knowledge_base)
    assert payload["triage"]["recommended_pathway"] == case["expected_pathway"]


@pytest.mark.parametrize("index", range(5))
def test_demo_scenario_sha_fund(index, demo_cases, knowledge_base):
    """Each scenario names the correct SHA fund - PHF, SHIF or ECCIF."""
    case = demo_cases[index]
    payload = _triage(case, knowledge_base)
    assert payload["triage"]["sha_fund"] == case["expected_sha_fund"]


def test_demo_level_distribution(demo_cases, knowledge_base):
    """The demo must actually cover all three levels, or it is a weak demo."""
    levels = {_triage(case, knowledge_base)["triage"]["triage_level"] for case in demo_cases}
    assert levels == {"RED", "YELLOW", "GREEN"}, f"Demo only covers {levels}"


@pytest.mark.parametrize("index", range(5))
def test_demo_scenario_produces_patient_facing_output(index, demo_cases, knowledge_base):
    """Every scenario must yield printable, non-empty patient instructions."""
    case = demo_cases[index]
    pathway = _triage(case, knowledge_base)["care_pathway"]
    assert pathway["patient_instruction"].strip()
    assert pathway["actions"], "care pathway has no action list"
    assert pathway["danger_signs_to_watch"], "no danger signs to watch"
    assert pathway["cost"]["statement"].strip(), "no cost statement"
    assert "SHA" in pathway["cost"]["statement"] or "NHIF" not in pathway["cost"]["statement"]


@pytest.mark.parametrize("index", range(5))
def test_no_nhif_references_anywhere(index, demo_cases, knowledge_base):
    """NHIF was replaced in October 2024; a stale reference would be a credibility bug."""
    payload = _triage(demo_cases[index], knowledge_base)
    serialised = str(payload).lower()
    assert "nhif" not in serialised, "Output still references the defunct NHIF scheme"


@pytest.mark.parametrize("index", range(5))
def test_demo_scenario_within_sla(index, demo_cases, knowledge_base):
    """The <30 second product requirement must hold deterministically."""
    payload = _triage(demo_cases[index], knowledge_base)
    assert payload["audit"]["total_ms"] < 30_000


def test_all_rule_fields_are_resolvable(knowledge_base):
    """A rule pointing at a field the engine cannot resolve would silently never match."""
    unknown = unknown_referenced_fields(knowledge_base.rules)
    assert not unknown, f"Rules reference fields the engine cannot resolve: {sorted(unknown)}"


def test_rules_are_priority_ordered(knowledge_base):
    priorities = [rule["priority"] for rule in knowledge_base.rules]
    assert priorities == sorted(priorities), "Rules must be evaluated in priority order"


def test_red_rules_are_evaluated_before_yellow_and_green(knowledge_base):
    """Acuity must never be shadowed: every RED priority precedes all YELLOW/GREEN."""
    last_red = max(
        (rule["priority"] for rule in knowledge_base.rules if rule["triage_level"] == "RED"),
        default=0,
    )
    first_non_red = min(
        (rule["priority"] for rule in knowledge_base.rules if rule["triage_level"] != "RED"),
        default=10_000,
    )
    assert last_red < first_non_red, "A non-RED rule is evaluated before a RED rule"


class TestRegressionCases:
    """Additional cases beyond the 5 demo scenarios."""

    @pytest.mark.parametrize(
        "case_id",
        ["sw-01", "preg-01", "tb-01", "dka-01", "uti-01"],
    )
    def test_regression_case(self, case_id, regression_cases, knowledge_base):
        case = next((item for item in regression_cases if item["case_id"] == case_id), None)
        assert case is not None, f"regression case {case_id} is missing"
        payload = _triage(case, knowledge_base)
        assert payload["triage"]["triage_level"] == case["expected_triage_level"], (
            f"{case_id}: expected {case['expected_triage_level']}, "
            f"got {payload['triage']['triage_level']} ({case['why']})"
        )


def test_swahili_and_english_inputs_agree(knowledge_base):
    """Swahili input must not triage differently from the equivalent English input."""
    english = run_full_triage(
        symptoms="I have high fever, headache and body aches for three days.",
        patient_age=30,
        language="en",
        knowledge_base=knowledge_base,
        use_llm=False,
    ).to_dict()
    swahili = run_full_triage(
        symptoms="Nina homa kali, maumivu ya kichwa na maumivu ya mwili kwa siku tatu.",
        patient_age=30,
        language="sw",
        knowledge_base=knowledge_base,
        use_llm=False,
    ).to_dict()
    assert english["triage"]["triage_level"] == swahili["triage"]["triage_level"]

    # The Swahili response must actually be in Swahili.
    instruction = swahili["care_pathway"]["patient_instruction"]
    assert any(word in instruction.lower() for word in ("nenda", "kliniki", "hospitalini", "pumzika", "kunywa"))
