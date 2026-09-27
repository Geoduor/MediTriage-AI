"""API-level tests. These confirm the endpoints Person 2's frontend will call.

TestClient is used directly, so no server needs to be running.
"""
from __future__ import annotations

import pytest

MALARIA_PAYLOAD = {
    "symptoms": "I have been having high fever for 2 days, with chills, severe headache, "
    "and my whole body aches. I also feel nauseous.",
    "patient_age": 25,
    "patient_context": {"hiv_status": "negative", "pregnant": False, "chronic_conditions": []},
    "language": "en",
}


class TestHealth:
    def test_health_is_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["checks"]["knowledge_base_loaded"] is True
        assert body["checks"]["demo_scenarios_present"] is True

    def test_health_reports_sha_funds(self, client):
        body = client.get("/health").json()
        assert body["checks"]["sha_benefits_present"] is True
        assert body["knowledge_base"]["sha_funds"] == 3

    def test_root_is_not_404(self, client):
        """A judge pasting the bare Render URL must not see a 404."""
        response = client.get("/")
        assert response.status_code == 200
        assert "endpoints" in response.json()


class TestFullTriage:
    def test_full_triage_malaria(self, client):
        response = client.post("/api/full-triage", json=MALARIA_PAYLOAD)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["triage"]["triage_level"] == "YELLOW"
        assert body["care_pathway"]["patient_instruction"]
        assert body["audit"]["within_sla"] is True

    def test_response_shape_is_stable(self, client):
        """The frontend depends on these keys; changing them is a breaking change."""
        body = client.post("/api/full-triage", json=MALARIA_PAYLOAD).json()
        assert set(body) == {"triage", "symptom_analysis", "care_pathway", "audit"}
        assert set(body["triage"]) >= {
            "triage_level", "urgency", "rationale", "recommended_pathway",
            "sha_fund", "colour", "label_en", "label_sw", "matched_rule",
        }
        assert set(body["care_pathway"]) >= {
            "patient_instruction", "actions", "facility", "sha", "cost",
            "what_to_bring", "danger_signs_to_watch", "disclaimer",
        }

    def test_emergency_case(self, client):
        response = client.post(
            "/api/full-triage",
            json={
                "symptoms": "Severe chest pain, pressure in my chest, I cannot breathe, I am sweating",
                "patient_age": 52,
            },
        )
        body = response.json()
        assert body["triage"]["triage_level"] == "RED"
        assert body["triage"]["sha_fund"] == "ECCIF"
        assert body["care_pathway"]["facility"]["level"] == "sub_county_hospital"

    def test_swahili_request(self, client):
        response = client.post(
            "/api/full-triage",
            json={
                "symptoms": "Nina homa kali, maumivu ya kichwa na maumivu ya mwili kwa siku tatu.",
                "patient_age": 30,
                "language": "sw",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["triage"]["triage_level"] == "YELLOW"
        assert body["care_pathway"]["language"] == "sw"

    def test_validation_rejects_blank_symptoms(self, client):
        response = client.post("/api/full-triage", json={"symptoms": "   "})
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_request"

    def test_validation_rejects_impossible_age(self, client):
        response = client.post(
            "/api/full-triage", json={"symptoms": "fever", "patient_age": 500}
        )
        assert response.status_code == 422


class TestIndividualAgents:
    def test_analyze_symptoms_endpoint(self, client):
        response = client.post("/api/analyze-symptoms", json=MALARIA_PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["primary_symptom"]
        assert "extraction_method" in body

    def test_triage_decision_endpoint(self, client):
        analysis = client.post("/api/analyze-symptoms", json=MALARIA_PAYLOAD).json()
        response = client.post("/api/triage-decision", json={"symptom_profile": analysis})
        assert response.status_code == 200
        body = response.json()
        assert body["triage_level"] in {"RED", "YELLOW", "GREEN"}
        assert body["explanation"]

    def test_care_pathway_endpoint(self, client):
        response = client.post(
            "/api/care-pathway",
            json={"triage_level": "RED", "symptom_profile": {"primary_symptom": "chest_pain"}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sha"]["fund_code"] == "PHF" or body["cost"]["statement"]
        assert body["danger_signs_to_watch"]

    def test_triage_decision_rejects_empty_profile(self, client):
        response = client.post("/api/triage-decision", json={"symptom_profile": {}})
        assert response.status_code == 422


class TestDemoSupport:
    def test_test_cases_endpoint_serves_five_scenarios(self, client):
        response = client.get("/api/demo/test-cases")
        assert response.status_code == 200
        body = response.json()
        assert len(body["test_cases"]) == 5
        assert len(body["regression_cases"]) >= 5
        for case in body["test_cases"]:
            assert case["symptoms"]
            assert case["expected_triage_level"] in {"RED", "YELLOW", "GREEN"}

    def test_rules_endpoint_is_reviewable(self, client):
        response = client.get("/api/rules")
        assert response.status_code == 200
        body = response.json()
        assert len(body["rules"]) > 10
        assert body["evaluation"]["default_level"] == "GREEN"

    def test_knowledge_base_reload(self, client):
        response = client.post("/api/admin/reload-knowledge-base")
        assert response.status_code == 200
        assert response.json()["status"] == "reloaded"


class TestDeterministicGuarantee:
    def test_same_input_gives_same_output(self, client):
        """Reproducibility is the whole point of a rule-based router."""
        first = client.post("/api/full-triage", json=MALARIA_PAYLOAD).json()
        second = client.post("/api/full-triage", json=MALARIA_PAYLOAD).json()
        assert first["triage"] == second["triage"]

    def test_triage_level_does_not_depend_on_the_llm(self, client):
        """With LLM_MODE=off the audit block must say so, and still triage."""
        body = client.post("/api/full-triage", json=MALARIA_PAYLOAD).json()
        assert body["audit"]["llm"]["enabled"] is False
        assert body["audit"]["deterministic_core"] is True
        assert body["triage"]["triage_level"] == "YELLOW"

    def test_latency_is_far_below_the_sla(self, client):
        body = client.post("/api/full-triage", json=MALARIA_PAYLOAD).json()
        # Offline path should be milliseconds, not seconds.
        assert body["audit"]["total_ms"] < 5_000, f"unexpectedly slow: {body['audit']}"
