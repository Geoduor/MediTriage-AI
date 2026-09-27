"""Debug helper: show exactly what the extractor and rule engine see.

Run:
    cd backend
    python debug_case.py "the symptom text" [age]

Person 1's diagnostic tool. When a scenario triages unexpectedly, run it here
first rather than guessing which rule fired.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from knowledge.loader import load_knowledge_base  # noqa: E402
from triage.engine import rule_matches, triage  # noqa: E402
from triage.extractor import extract_features  # noqa: E402


def debug(text: str, age: int | None = None, context: dict | None = None) -> None:
    kb = load_knowledge_base()
    profile = extract_features(text, age, context or {})

    print("=" * 78)
    print(f"TEXT: {text}")
    print("=" * 78)
    print(f"primary symptom   : {profile['primary_symptom']}")
    print(f"all symptoms      : {profile['all_symptoms']}")
    print(f"severity          : {profile['severity']}")
    print(f"duration_days     : {profile['duration_days']}")
    print(f"temperature       : {profile['extracted']['temperature_celsius']}")
    print(f"red flags         : {profile['red_flags']}")
    print(f"features          : {profile['features']}")
    print(f"patient           : {profile['patient']}")

    print("\nMATCHING RULES (in priority order):")
    match = triage(profile, kb.rules, kb.rule_meta)
    for rule in kb.rules:
        if rule_matches(profile, rule):
            marker = "-->" if rule["rule_id"] == match.rule_id else "   "
            print(f"  {marker} {rule['priority']:>4}  {rule['rule_id']:<6} {rule['triage_level']:<7} {rule['name']}")

    print(f"\nDECISION: {match.triage_level}  via {match.rule_id}  -> {match.recommended_pathway}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    age_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    debug(sys.argv[1], age_arg)
