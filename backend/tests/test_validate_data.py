"""Tests for Person 3's data QA validator (`backend/data/validate_data.py`).

Why this file exists
--------------------
The validator shipped with a check that validated nothing: it read a
`sha_benefits.json` key (`benefits`) that the real schema does not use, so a
broken SHA dataset would still have printed success. A QA tool that cannot fail
is worse than no tool, because it creates false confidence.

These tests therefore do two things:
  1. assert the validator passes on the real, shipped data, and
  2. assert it FAILS when the data is deliberately corrupted - proving each
     check actually fires.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
VALIDATOR = DATA_DIR / "validate_data.py"


def run_validator(data_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(data_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


@pytest.fixture
def data_copy():
    """A writable copy of the knowledge base that tests may corrupt.

    Deliberately not pytest's `tmp_path`: in confined/sandboxed environments the
    system temp directory can be unwritable, which makes every test in this file
    error at setup instead of testing anything. A scratch directory beside this
    test file is reliably writable everywhere and is removed afterwards.
    """
    base = Path(__file__).resolve().parent / "_data_copy_scratch"
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(DATA_DIR, base)
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _patch(path: Path, mutate) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


class TestValidatorOnRealData:
    def test_shipped_data_passes(self):
        result = run_validator(DATA_DIR)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "all data files valid" in result.stdout

    def test_output_is_ascii_only(self):
        """The original emoji output raised UnicodeEncodeError on a cp1252 console."""
        result = run_validator(DATA_DIR)
        result.stdout.encode("ascii")  # raises if any non-ASCII character remains

    def test_reports_counts(self):
        result = run_validator(DATA_DIR)
        assert "10 conditions" in result.stdout
        assert "26 triage rules" in result.stdout


class TestValidatorCatchesCorruption:
    """Each test proves one check is live rather than decorative."""

    def test_missing_file(self, data_copy: Path):
        (data_copy / "triage_rules.json").unlink()
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "MISSING FILE: triage_rules.json" in result.stdout

    def test_invalid_json(self, data_copy: Path):
        (data_copy / "conditions.json").write_text("{ not json", encoding="utf-8")
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "INVALID JSON in conditions.json" in result.stdout

    def test_broken_sha_benefits_structure(self, data_copy: Path):
        """The regression that motivated this file: SHA checks must not be a no-op."""
        _patch(data_copy / "sha_benefits.json", lambda doc: doc.pop("funds"))
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "funds" in result.stdout

    def test_unknown_sha_fund_code(self, data_copy: Path):
        _patch(
            data_copy / "sha_benefits.json",
            lambda doc: doc["facility_levels"][0].update({"sha_fund": "NHIF"}),
        )
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "unknown fund" in result.stdout

    def test_facility_level_missing_field(self, data_copy: Path):
        _patch(
            data_copy / "sha_benefits.json",
            lambda doc: doc["facility_levels"][0].pop("patient_cost_kes"),
        )
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "patient_cost_kes" in result.stdout

    def test_condition_missing_required_field(self, data_copy: Path):
        _patch(data_copy / "conditions.json", lambda doc: doc["conditions"][0].pop("sha_fund"))
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "missing 'sha_fund'" in result.stdout

    def test_invalid_triage_level_in_rules(self, data_copy: Path):
        _patch(
            data_copy / "triage_rules.json",
            lambda doc: doc["rules"][0].update({"triage_level": "ORANGE"}),
        )
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "invalid triage_level" in result.stdout

    def test_red_rule_shadowed_by_non_red(self, data_copy: Path):
        """Acuity shadowing would be clinically dangerous, so it must be caught."""
        _patch(
            data_copy / "triage_rules.json",
            lambda doc: doc["rules"][0].update({"triage_level": "GREEN", "priority": 1}),
        )
        result = run_validator(data_copy)
        assert result.returncode == 1
        # Either the ordering check or the shadowing check must fire.
        assert "shadowed" in result.stdout or "ascending priority" in result.stdout

    def test_wrong_number_of_demo_scenarios(self, data_copy: Path):
        _patch(data_copy / "test_cases.json", lambda doc: doc["test_cases"].pop())
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "expected 5 demo scenarios" in result.stdout

    def test_demo_scenarios_must_cover_all_levels(self, data_copy: Path):
        _patch(
            data_copy / "test_cases.json",
            lambda doc: [tc.update({"expected_triage_level": "GREEN"}) for tc in doc["test_cases"]],
        )
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "all three levels" in result.stdout

    def test_duplicate_scenario_ids(self, data_copy: Path):
        _patch(
            data_copy / "test_cases.json",
            lambda doc: doc["test_cases"][1].update({"scenario_id": doc["test_cases"][0]["scenario_id"]}),
        )
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "duplicate scenario_id" in result.stdout

    def test_missing_swahili_section(self, data_copy: Path):
        _patch(data_copy / "swahili_translations.json", lambda doc: doc.pop("instructions"))
        result = run_validator(data_copy)
        assert result.returncode == 1
        assert "instructions" in result.stdout
