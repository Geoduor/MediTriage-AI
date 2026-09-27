"""Tests for the rule engine itself, independent of any particular scenario.

If these fail, the demo scenarios will fail too - they are the earlier warning.
"""
from __future__ import annotations

import pytest

from triage.engine import (
    LEVEL_META,
    evaluate_predicate,
    known_field_paths,
    referenced_fields,
    resolve_path,
    rule_matches,
    triage,
    unknown_referenced_fields,
)


class TestPredicates:
    profile = {
        "primary_symptom": "chest_pain",
        "all_symptoms": ["chest_pain", "difficulty_breathing", "sweating"],
        "red_flags": ["difficulty breathing with chest pain"],
        "severity": "severe",
        "duration_days": 21,
        "features": {"fever_present": True, "fever_high": False, "has_red_flag": True},
        "patient": {"age": 45, "pregnant": False, "chronic": ["diabetes"]},
    }

    def test_any_operator(self):
        assert evaluate_predicate(self.profile, {"field": "symptoms.all", "any": ["chest pain"]})
        assert not evaluate_predicate(self.profile, {"field": "symptoms.all", "any": ["toothache"]})

    def test_any_is_case_insensitive(self):
        assert evaluate_predicate(self.profile, {"field": "symptoms.all", "any": ["CHEST PAIN"]})

    def test_all_operator_requires_every_needle(self):
        assert evaluate_predicate(self.profile, {"field": "symptoms.all", "all": ["chest", "breath"]})
        assert not evaluate_predicate(self.profile, {"field": "symptoms.all", "all": ["chest", "tooth"]})

    def test_none_operator(self):
        assert evaluate_predicate(self.profile, {"field": "symptoms.all", "none": ["toothache"]})
        assert not evaluate_predicate(self.profile, {"field": "symptoms.all", "none": ["chest"]})

    def test_eq_on_boolean(self):
        assert evaluate_predicate(self.profile, {"field": "features.fever_present", "eq": True})
        assert not evaluate_predicate(self.profile, {"field": "features.fever_high", "eq": True})

    def test_eq_on_string(self):
        assert evaluate_predicate(self.profile, {"field": "severity", "eq": "severe"})
        assert not evaluate_predicate(self.profile, {"field": "severity", "eq": "mild"})

    def test_numeric_comparison(self):
        assert evaluate_predicate(self.profile, {"field": "duration_days", "gte": 14})
        assert not evaluate_predicate(self.profile, {"field": "duration_days", "lt": 7})

    def test_exists_operator(self):
        assert evaluate_predicate(self.profile, {"field": "features.fever_present", "exists": True})
        assert evaluate_predicate(self.profile, {"field": "features.missing_key", "exists": False})

    def test_missing_field_does_not_match_any(self):
        assert not evaluate_predicate(self.profile, {"field": "features.nonexistent", "any": ["x"]})

    def test_predicate_without_operator_raises(self):
        from triage.engine import RuleEngineError

        with pytest.raises(RuleEngineError):
            evaluate_predicate(self.profile, {"field": "severity"})

    def test_predicate_without_field_raises(self):
        from triage.engine import RuleEngineError

        with pytest.raises(RuleEngineError):
            evaluate_predicate(self.profile, {"any": ["x"]})


class TestPathResolution:
    profile = {
        "primary_symptom": "fever",
        "associated_symptoms": ["headache"],
        "all_symptoms": ["fever", "headache"],
        "features": {"fever_present": True},
        "patient": {"pregnant": True, "chronic": ["hypertension"]},
    }

    def test_primary_alias(self):
        assert resolve_path(self.profile, "symptoms.primary") == "fever"

    def test_all_alias_merges_lists(self):
        merged = resolve_path(self.profile, "symptoms.all")
        assert "fever" in merged
        assert "headache" in merged

    def test_nested_feature_path(self):
        assert resolve_path(self.profile, "features.fever_present") is True

    def test_unknown_path_returns_none(self):
        assert resolve_path(self.profile, "does.not.exist") is None


class TestRulesetIntegrity:
    def test_rule_matches_requires_all_predicates(self, knowledge_base):
        """A rule with two predicates must not match on one of them alone."""
        rule = next(
            rule for rule in knowledge_base.rules if rule["rule_id"] == "r001"
        )
        profile_needing_both = {
            "primary_symptom": "chest_pain",
            "all_symptoms": ["chest_pain", "difficulty_breathing"],
            "red_flags": [],
            "features": {"has_red_flag": False},
        }
        assert rule_matches(profile_needing_both, rule)

        only_chest_pain = {
            "primary_symptom": "chest_pain",
            "all_symptoms": ["chest_pain"],
            "red_flags": [],
            "features": {"has_red_flag": False},
        }
        assert not rule_matches(only_chest_pain, rule)

    def test_every_level_exists_in_the_ruleset(self, knowledge_base):
        levels = {rule["triage_level"] for rule in knowledge_base.rules}
        assert levels == {"RED", "YELLOW", "GREEN"}

    def test_level_meta_covers_every_level(self):
        assert set(LEVEL_META) == {"RED", "YELLOW", "GREEN"}

    def test_no_unknown_fields_referenced(self, knowledge_base):
        assert not unknown_referenced_fields(knowledge_base.rules)

    def test_known_paths_superset_of_referenced(self, knowledge_base):
        assert referenced_fields(knowledge_base.rules) <= known_field_paths()

    def test_default_rule_is_last(self, knowledge_base):
        assert knowledge_base.rules[-1]["rule_id"] == "r999"
        assert knowledge_base.rules[-1]["predicates"] == []

    def test_empty_profile_hits_the_default_rule(self, knowledge_base):
        """An empty profile must not accidentally match a clinical rule."""
        match = triage({}, knowledge_base.rules, knowledge_base.rule_meta)
        assert match.rule_id == "r999"
        assert match.triage_level == "GREEN"

    def test_no_blank_rationales(self, knowledge_base):
        for rule in knowledge_base.rules:
            assert rule.get("rationale", "").strip(), f"{rule['rule_id']} has no rationale"

    def test_sha_fund_values_are_known(self, knowledge_base):
        valid = {fund["code"] for fund in knowledge_base.sha_benefits["funds"]}
        for rule in knowledge_base.rules:
            fund = rule.get("sha_fund")
            if fund:
                assert fund in valid, f"{rule['rule_id']} references unknown SHA fund {fund}"


class TestKnowledgeBaseContent:
    def test_ten_conditions(self, knowledge_base):
        assert len(knowledge_base.conditions) == 10

    def test_conditions_have_required_fields(self, knowledge_base):
        required = {"id", "slug", "name", "symptoms", "red_flag_indicators", "sha_covered", "sha_fund"}
        for condition in knowledge_base.conditions:
            missing = required - set(condition)
            assert not missing, f"{condition.get('name')} is missing {missing}"

    def test_no_legacy_nhif_fields(self, knowledge_base):
        """`nhif_covered` was the old schema; SHA replaced NHIF in October 2024."""
        for condition in knowledge_base.conditions:
            assert "nhif_covered" not in condition, f"{condition['name']} still uses nhif_covered"

    def test_sha_has_three_funds(self, knowledge_base):
        codes = {fund["code"] for fund in knowledge_base.sha_benefits["funds"]}
        assert codes == {"PHF", "SHIF", "ECCIF"}

    def test_swahili_translations_have_corrected_terms(self, knowledge_base):
        symptoms = knowledge_base.swahili["symptoms"]
        assert symptoms["fever"] == "homa", "fever must be 'homa', not 'moto'"
        assert symptoms["diarrhoea"] == "kuhara", "diarrhoea must be 'kuhara', not 'Kuvimba'"

    def test_clinical_review_is_flagged_as_pending(self, knowledge_base):
        """We must never imply clinician sign-off we do not have."""
        unreviewed = [c for c in knowledge_base.conditions if not c.get("clinical_reviewed")]
        assert unreviewed, "expected clinical_reviewed=False until a clinician signs off"
