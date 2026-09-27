"""
validate_data.py - data QA for the MediTriage knowledge base.

Originally written by Person 3 (evance-coder); corrected and adapted to the
shipped JSON schema by Person 1 after integration testing found three defects:

  1. The filename was `validate_data (1).py` (a browser-upload artifact with a
     space and parentheses), so the documented command `python validate_data.py`
     could not work. Renamed.
  2. The success/failure output used emoji, which raises UnicodeEncodeError on a
     Windows cp1252 console - it crashed at the final print AFTER all checks had
     passed, making a healthy dataset look broken. Output is now plain ASCII.
  3. `check_sha_benefits` read `data["benefits"]`, but the shipped
     `sha_benefits.json` stores `funds` and `facility_levels`. It therefore
     validated nothing at all for SHA while reporting success. It now checks the
     real structure.

Run before every demo rehearsal:

    python backend/data/validate_data.py

Optionally validate a different directory (used by the test suite):

    python backend/data/validate_data.py /path/to/copy/of/data

Exits non-zero on failure, so it can be wired into CI. For deeper checks
(rule ordering, resolvable rule fields, engine behaviour) see the pytest suite:
`cd backend && python -m pytest tests/ -q`.
"""

import json
import sys
from pathlib import Path

# Allow the test suite to point the validator at a corrupted copy of the data
# so it can prove the checks actually fire, instead of trusting that they do.
DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
VALID_TRIAGE_LEVELS = {"RED", "YELLOW", "GREEN"}
VALID_SHA_FUND_CODES = {"PHF", "SHIF", "ECCIF"}

errors = []


def load_json(filename):
    path = DATA_DIR / filename
    if not path.exists():
        errors.append(f"MISSING FILE: {filename}")
        return None
    try:
        # Always read as UTF-8: the default is cp1252 on Windows, which cannot
        # decode non-ASCII characters (degree signs, Swahili accents).
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"INVALID JSON in {filename}: {e}")
        return None
    except UnicodeDecodeError as e:
        errors.append(f"NOT VALID UTF-8: {filename}: {e}")
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
    for c in data.get("conditions", []):
        fund = str(c.get("sha_fund", ""))
        if fund and not any(code in fund for code in VALID_SHA_FUND_CODES):
            errors.append(
                f"conditions.json: condition id={c.get('id')} references no known SHA fund ({fund[:60]!r})"
            )


def check_triage_rules(data):
    if not data:
        return
    rules = data.get("rules", [])
    if not rules:
        errors.append("triage_rules.json: no rules found")
        return
    for r in rules:
        if r.get("triage_level") not in VALID_TRIAGE_LEVELS:
            errors.append(
                f"triage_rules.json: rule {r.get('rule_id')} has invalid triage_level {r.get('triage_level')!r}"
            )
        if not r.get("rationale"):
            errors.append(f"triage_rules.json: rule {r.get('rule_id')} has no rationale")

    # Priority ordering matters: the engine returns the FIRST match, so a
    # non-RED rule evaluated before a RED rule would shadow a life-threatening
    # presentation. The pytest suite asserts this too - checked here so the data
    # owner sees it in their own tool.
    levels_by_priority = [
        (r.get("priority", 9999), r.get("triage_level"), r.get("rule_id")) for r in rules
    ]
    if [p for p, _, _ in levels_by_priority] != sorted(p for p, _, _ in levels_by_priority):
        errors.append("triage_rules.json: rules are not in ascending priority order")
    last_red = max((p for p, lvl, _ in levels_by_priority if lvl == "RED"), default=0)
    first_non_red = min((p for p, lvl, _ in levels_by_priority if lvl != "RED"), default=10_000)
    if last_red >= first_non_red:
        errors.append(
            f"triage_rules.json: a non-RED rule (priority {first_non_red}) is evaluated before "
            f"a RED rule (priority {last_red}) - acuity would be shadowed"
        )


def check_test_cases(data):
    if not data:
        return
    cases = data.get("test_cases", [])
    if len(cases) != 5:
        errors.append(f"test_cases.json: expected 5 demo scenarios, found {len(cases)}")
    seen = set()
    for tc in cases:
        sid = tc.get("scenario_id")
        if sid in seen:
            errors.append(f"test_cases.json: duplicate scenario_id {sid}")
        seen.add(sid)
        if tc.get("expected_triage_level") not in VALID_TRIAGE_LEVELS:
            errors.append(
                f"test_cases.json: scenario {sid} has invalid expected_triage_level "
                f"{tc.get('expected_triage_level')!r}"
            )
        if not tc.get("symptoms"):
            errors.append(f"test_cases.json: scenario {sid} has no symptoms text")
        if not tc.get("expected_pathway"):
            errors.append(f"test_cases.json: scenario {sid} has no expected_pathway")

    levels = {tc.get("expected_triage_level") for tc in cases}
    if levels != VALID_TRIAGE_LEVELS:
        errors.append(
            f"test_cases.json: the 5 demo scenarios should cover all three levels, found {sorted(levels)}"
        )

    for rc in data.get("additional_regression_cases", []):
        if rc.get("expected_triage_level") not in VALID_TRIAGE_LEVELS:
            errors.append(
                f"test_cases.json: regression case {rc.get('case_id')} has invalid expected_triage_level"
            )


def check_sha_benefits(data):
    """Validate the real sha_benefits.json structure (funds + facility_levels).

    The original version read a `benefits` key that this schema does not have,
    so it silently passed without checking anything.
    """
    if not data:
        return
    funds = data.get("funds", [])
    if not funds:
        errors.append("sha_benefits.json: no 'funds' found (expected PHF, SHIF and ECCIF)")
    codes = {f.get("code") for f in funds}
    if codes != VALID_SHA_FUND_CODES:
        errors.append(f"sha_benefits.json: expected fund codes {sorted(VALID_SHA_FUND_CODES)}, found {sorted(codes)}")
    for f in funds:
        for field in ("code", "name", "purpose", "covers", "patient_cost"):
            if not f.get(field):
                errors.append(f"sha_benefits.json: fund {f.get('code')} missing '{field}'")

    levels = data.get("facility_levels", [])
    if not levels:
        errors.append("sha_benefits.json: no 'facility_levels' found")
    for level in levels:
        for field in ("level", "services", "sha_fund", "patient_cost_kes"):
            if level.get(field) in (None, "", []):
                errors.append(f"sha_benefits.json: facility level {level.get('level')} missing '{field}'")
        if level.get("sha_fund") and level["sha_fund"] not in VALID_SHA_FUND_CODES:
            errors.append(
                f"sha_benefits.json: facility level {level.get('level')} references unknown fund "
                f"{level.get('sha_fund')!r}"
            )


def main():
    conditions = load_json("conditions.json")
    rules = load_json("triage_rules.json")
    test_cases = load_json("test_cases.json")
    benefits = load_json("sha_benefits.json")
    # Not required by the agents, but a missing translation file would break the
    # Swahili pathway silently, so validate it if it is present.
    translations = load_json("swahili_translations.json")

    check_conditions(conditions)
    check_triage_rules(rules)
    check_test_cases(test_cases)
    check_sha_benefits(benefits)

    if translations is not None:
        for section in ("symptoms", "triage_levels", "instructions", "cost"):
            if not translations.get(section):
                errors.append(f"swahili_translations.json: missing '{section}' section")

    if errors:
        print(f"FAILED: {len(errors)} problem(s) found:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("OK: all data files valid - conditions.json, triage_rules.json, test_cases.json, sha_benefits.json")
    print(
        f"    {len(conditions.get('conditions', []))} conditions, "
        f"{len(rules.get('rules', []))} triage rules, "
        f"{len(test_cases.get('test_cases', []))} demo scenarios, "
        f"{len(test_cases.get('additional_regression_cases', []))} regression cases."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
