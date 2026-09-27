"""
validate_data.py — Person 3's data QA script.

Run before every demo rehearsal:
    python validate_data.py

Checks that conditions.json, sha_benefits.json, triage_rules.json, and
test_cases.json are valid JSON, have the fields the agents expect, and
that test case IDs/expected triage levels are internally consistent.
Exits non-zero on failure so it can be wired into a CI step if Geofry wants one.
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent
VALID_TRIAGE_LEVELS = {"RED", "YELLOW", "GREEN"}
VALID_SHA_FUNDS_KEYWORDS = ["Primary Healthcare Fund", "SHIF", "ECCIF", "Social Health Insurance Fund",
                            "Emergency, Chronic and Critical Illness Fund"]

errors = []


def load_json(filename):
    path = DATA_DIR / filename
    if not path.exists():
        errors.append(f"MISSING FILE: {filename}")
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"INVALID JSON in {filename}: {e}")
        return None


def check_conditions(data):
    if not data:
        return
    required = ["id", "name", "symptoms", "red_flag_indicators", "sha_covered", "sha_fund"]
    for c in data.get("conditions", []):
        for field in required:
            if field not in c:
                errors.append(f"conditions.json: condition id={c.get('id')} missing '{field}'")
    ids = [c["id"] for c in data.get("conditions", [])]
    if len(ids) != len(set(ids)):
        errors.append("conditions.json: duplicate condition ids found")
    if len(ids) != 10:
        errors.append(f"conditions.json: expected 10 conditions, found {len(ids)}")


def check_triage_rules(data):
    if not data:
        return
    for r in data.get("rules", []):
        if r.get("triage_level") not in VALID_TRIAGE_LEVELS:
            errors.append(f"triage_rules.json: rule {r.get('rule_id')} has invalid triage_level")


def check_test_cases(data):
    if not data:
        return
    cases = data.get("test_cases", [])
    if len(cases) != 5:
        errors.append(f"test_cases.json: expected 5 demo scenarios, found {len(cases)}")
    for tc in cases:
        if tc.get("expected_triage_level") not in VALID_TRIAGE_LEVELS:
            errors.append(f"test_cases.json: scenario {tc.get('scenario_id')} has invalid expected_triage_level")
        if not tc.get("symptoms"):
            errors.append(f"test_cases.json: scenario {tc.get('scenario_id')} has no symptoms text")


def check_sha_benefits(data):
    if not data:
        return
    for b in data.get("benefits", []):
        fund = b.get("sha_fund", "")
        if not any(keyword in fund for keyword in VALID_SHA_FUNDS_KEYWORDS):
            errors.append(f"sha_benefits.json: benefit at facility_level={b.get('facility_level')} has an unrecognized sha_fund")


def main():
    conditions = load_json("conditions.json")
    rules = load_json("triage_rules.json")
    test_cases = load_json("test_cases.json")
    benefits = load_json("sha_benefits.json")

    check_conditions(conditions)
    check_triage_rules(rules)
    check_test_cases(test_cases)
    check_sha_benefits(benefits)

    if errors:
        print(f"❌ {len(errors)} problem(s) found:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("✅ All data files valid: conditions.json, triage_rules.json, test_cases.json, sha_benefits.json")
    print(f"   {len(conditions.get('conditions', []))} conditions, "
          f"{len(rules.get('rules', []))} triage rules, "
          f"{len(test_cases.get('test_cases', []))} test scenarios.")
    sys.exit(0)


if __name__ == "__main__":
    main()
