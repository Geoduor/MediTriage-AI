"""Loader for the JSON knowledge base owned by Person 3 (Data & Content Specialist).

The backend reads all clinical content from `backend/data/*.json`. Nothing
clinical is hardcoded in Python, so Person 3 can iterate on content without
touching engine code, and each change is covered by the scenario test suite.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)


class KnowledgeBaseError(RuntimeError):
    """Raised when the knowledge base is missing or malformed."""


@dataclass
class KnowledgeBase:
    """In-memory view of the JSON knowledge base."""

    conditions: list[dict[str, Any]] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)
    rule_meta: dict[str, Any] = field(default_factory=dict)
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    regression_cases: list[dict[str, Any]] = field(default_factory=list)
    sha_benefits: dict[str, Any] = field(default_factory=dict)
    swahili: dict[str, Any] = field(default_factory=dict)
    source_dir: Path | None = None

    # ---- convenience lookups -------------------------------------------------

    def condition_by_slug(self, slug: str) -> dict[str, Any] | None:
        for condition in self.conditions:
            if condition.get("slug") == slug:
                return condition
        return None

    def fund(self, code: str) -> dict[str, Any] | None:
        for fund in self.sha_benefits.get("funds", []):
            if fund.get("code") == code:
                return fund
        return None

    def facility_levels(self) -> list[dict[str, Any]]:
        return self.sha_benefits.get("facility_levels", [])

    def summary(self) -> dict[str, Any]:
        return {
            "conditions": len(self.conditions),
            "rules": len(self.rules),
            "demo_scenarios": len(self.test_cases),
            "regression_cases": len(self.regression_cases),
            "sha_funds": len(self.sha_benefits.get("funds", [])),
            "swahili_symptoms": len(self.swahili.get("symptoms", {})),
            "source_dir": str(self.source_dir),
        }


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise KnowledgeBaseError(
            f"Knowledge base file is missing: {path}. "
            "Expected the JSON files from Person 3 under backend/data/."
        )
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise KnowledgeBaseError(f"{path.name} is not valid JSON: {exc}") from exc


def _resolve_data_dir(data_dir: Path | None = None) -> Path:
    candidate = Path(data_dir) if data_dir else get_settings().data_dir
    if candidate.exists():
        return candidate
    # Fall back to the directory next to this package so the app still boots
    # when the process working directory is not the repo root.
    fallback = Path(__file__).resolve().parents[1] / "data"
    if fallback.exists():
        return fallback
    raise KnowledgeBaseError(
        f"No knowledge base directory found. Looked in: {candidate} and {fallback}"
    )


def load_knowledge_base(data_dir: Path | None = None) -> KnowledgeBase:
    """Read and validate every JSON knowledge base file."""
    directory = _resolve_data_dir(data_dir)

    conditions_doc = _read_json(directory / "conditions.json")
    rules_doc = _read_json(directory / "triage_rules.json")
    test_cases_doc = _read_json(directory / "test_cases.json")
    sha_doc = _read_json(directory / "sha_benefits.json")
    swahili_doc = _read_json(directory / "swahili_translations.json")

    rules = rules_doc.get("rules", [])
    if not rules:
        raise KnowledgeBaseError("triage_rules.json contains no rules.")

    # Fail loudly at startup rather than silently at demo time: the rules must
    # be ordered, complete and unambiguous.
    seen_ids: set[str] = set()
    for rule in rules:
        rule_id = rule.get("rule_id")
        if not rule_id:
            raise KnowledgeBaseError(f"A rule is missing rule_id: {rule!r}")
        if rule_id in seen_ids:
            raise KnowledgeBaseError(f"Duplicate rule_id in triage_rules.json: {rule_id}")
        seen_ids.add(rule_id)
        if rule.get("triage_level") not in {"RED", "YELLOW", "GREEN"}:
            raise KnowledgeBaseError(
                f"Rule {rule_id} has an invalid triage_level: {rule.get('triage_level')!r}"
            )
        if not rule.get("predicates") and rule_id != "r999":
            logger.warning("Rule %s has no predicates but is not the default rule.", rule_id)
        if rule.get("predicates") and rule.get("priority", 0) >= 999:
            raise KnowledgeBaseError(
                f"Rule {rule_id} has predicates but default-level priority; unreachable."
            )

    rules_sorted = sorted(rules, key=lambda rule: rule.get("priority", 9999))

    kb = KnowledgeBase(
        conditions=conditions_doc.get("conditions", []),
        rules=rules_sorted,
        rule_meta={key: value for key, value in rules_doc.items() if key != "rules"},
        test_cases=test_cases_doc.get("test_cases", []),
        regression_cases=test_cases_doc.get("additional_regression_cases", []),
        sha_benefits=sha_doc,
        swahili=swahili_doc,
        source_dir=directory,
    )

    logger.info("Knowledge base loaded: %s", kb.summary())
    return kb


_CACHE: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """Process-wide cached knowledge base."""
    global _CACHE
    if _CACHE is None:
        _CACHE = load_knowledge_base()
    return _CACHE


def reset_knowledge_base_cache() -> None:
    """Drop the cache (used by tests and by /admin/reload)."""
    global _CACHE
    _CACHE = None
