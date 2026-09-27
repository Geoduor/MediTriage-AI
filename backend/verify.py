"""Standalone end-to-end verification of the MediTriage pipeline.

Run:
    cd backend
    python verify.py

Why this exists alongside pytest: this script has **no third-party test
dependencies**. It is what you run on the demo laptop, or against a deployed
Render URL, when you need a definitive yes/no on whether the system is
behaving correctly.

    python verify.py                                  # local pipeline
    python verify.py --url https://host.onrender.com  # deployed service

Exit code 0 = every check passed. Non-zero = something is broken.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

PASS = "PASS"
FAIL = "FAIL"

results: list[tuple[str, str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    results.append((PASS if condition else FAIL, name, detail))
    marker = "  ok  " if condition else " FAIL "
    print(f"[{marker}] {name}" + (f"  -> {detail}" if detail and not condition else ""))
    return condition


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def verify_local() -> int:
    from knowledge.loader import load_knowledge_base
    from orchestrator import run_full_triage
    from triage.engine import unknown_referenced_fields

    section("1. Knowledge base")
    kb = load_knowledge_base()
    summary = kb.summary()
    print(json.dumps(summary, indent=2))
    check("10 conditions loaded", summary["conditions"] == 10, str(summary["conditions"]))
    check("demo scenarios present", summary["demo_scenarios"] == 5)
    check("SHA has three funds", summary["sha_funds"] == 3)
    check("all rule fields resolvable", not unknown_referenced_fields(kb.rules),
          str(sorted(unknown_referenced_fields(kb.rules))))

    last_red = max((r["priority"] for r in kb.rules if r["triage_level"] == "RED"), default=0)
    first_non_red = min((r["priority"] for r in kb.rules if r["triage_level"] != "RED"), default=10_000)
    check("no non-RED rule shadows a RED rule", last_red < first_non_red,
          f"last RED priority={last_red}, first non-RED={first_non_red}")
    check("default rule is last", kb.rules[-1]["rule_id"] == "r999")

    section("2. The 5 demo scenarios")
    all_ok = True
    for case in kb.test_cases:
        context = dict(case.get("patient_context") or {})
        if case.get("location"):
            context.setdefault("location", case["location"])
        outcome = run_full_triage(
            symptoms=case["symptoms"],
            patient_age=case.get("patient_age"),
            patient_context=context,
            language=case.get("language", "en"),
            sex=case.get("sex"),
            knowledge_base=kb,
            use_llm=False,
        ).to_dict()

        triage = outcome["triage"]
        pathway = outcome["care_pathway"]
        expected = case["expected_triage_level"]
        actual = triage["triage_level"]

        line_ok = check(
            f"Scenario {case['scenario_id']}: {case['patient_name']}",
            actual == expected,
            f"got {actual}, expected {expected} (rule {triage['matched_rule']['rule_id']})",
        )
        check(
            f"  pathway is '{case['expected_pathway']}'",
            triage["recommended_pathway"] == case["expected_pathway"],
            triage["recommended_pathway"],
        )
        check(
            f"  SHA fund is {case['expected_sha_fund']}",
            triage["sha_fund"] == case["expected_sha_fund"],
            str(triage["sha_fund"]),
        )
        check(
            "  patient instruction produced",
            bool(pathway.get("patient_instruction", "").strip()),
        )
        check("  within 30s SLA", outcome["audit"]["within_sla"],
              f"{outcome['audit']['total_ms']}ms")
        check("  no NHIF references", "nhif" not in json.dumps(outcome).lower())
        all_ok = all_ok and line_ok

        print(f"       level={actual}  rule={triage['matched_rule']['rule_id']}  "
              f"fund={triage['sha_fund']}  {outcome['audit']['total_ms']}ms")
        print(f"       -> {pathway['patient_instruction'][:110]}")

    check("demo covers all three levels",
          {run_full_triage(symptoms=c["symptoms"], patient_age=c.get("patient_age"),
                           patient_context=c.get("patient_context") or {},
                           knowledge_base=kb, use_llm=False).to_dict()["triage"]["triage_level"]
           for c in kb.test_cases} == {"RED", "YELLOW", "GREEN"})

    section("3. Regression cases")
    for case in kb.regression_cases:
        outcome = run_full_triage(
            symptoms=case["symptoms"],
            patient_age=case.get("patient_age"),
            patient_context=case.get("patient_context") or {},
            knowledge_base=kb,
            use_llm=False,
        ).to_dict()
        actual = outcome["triage"]["triage_level"]
        check(
            f"{case['case_id']}: {case['why'][:60]}",
            actual == case["expected_triage_level"],
            f"got {actual}, expected {case['expected_triage_level']}",
        )

    section("4. Swahili / English equivalence")
    english = run_full_triage(
        symptoms="I have high fever, headache and body aches for three days.",
        patient_age=30, knowledge_base=kb, use_llm=False,
    ).to_dict()
    swahili = run_full_triage(
        symptoms="Nina homa kali, maumivu ya kichwa na maumivu ya mwili kwa siku tatu.",
        patient_age=30, language="sw", knowledge_base=kb, use_llm=False,
    ).to_dict()
    check("same triage level in both languages",
          english["triage"]["triage_level"] == swahili["triage"]["triage_level"],
          f"en={english['triage']['triage_level']} sw={swahili['triage']['triage_level']}")
    instruction = swahili["care_pathway"]["patient_instruction"].lower()
    check("Swahili response is actually in Swahili",
          any(w in instruction for w in ("nenda", "kliniki", "hospitalini", "pumzika", "kunywa")),
          instruction[:80])

    section("5. Determinism and LLM independence")
    first = run_full_triage(symptoms="severe chest pain and I cannot breathe",
                            patient_age=52, knowledge_base=kb, use_llm=False).to_dict()
    second = run_full_triage(symptoms="severe chest pain and I cannot breathe",
                             patient_age=52, knowledge_base=kb, use_llm=False).to_dict()
    check("identical input gives identical triage", first["triage"] == second["triage"])
    check("audit reports the LLM as disabled", first["audit"]["llm"]["enabled"] is False)
    check("deterministic core flag set", first["audit"]["deterministic_core"] is True)

    return 0 if all_ok else 1


def verify_remote(url: str) -> int:
    """Verify a deployed instance over HTTP."""
    import urllib.error
    import urllib.request

    base = url.rstrip("/")
    section(f"Remote verification: {base}")

    def get(path: str):
        with urllib.request.urlopen(f"{base}{path}", timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))

    def post(path: str, payload: dict):
        request = urllib.request.Request(
            f"{base}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        health = get("/health")
    except Exception as exc:
        check("backend reachable", False, str(exc))
        return 1

    print(json.dumps(health, indent=2))
    check("backend reachable and healthy", health.get("status") == "ok")
    check("knowledge base loaded", health.get("checks", {}).get("knowledge_base_loaded") is True)
    check("5 demo scenarios served", health.get("checks", {}).get("demo_scenarios_present") is True)
    check("three SHA funds", health.get("checks", {}).get("sha_benefits_present") is True)

    section("Remote demo scenarios")
    cases = get("/api/demo/test-cases")["test_cases"]
    check("five scenarios returned", len(cases) == 5, str(len(cases)))

    all_ok = True
    for case in cases:
        context = dict(case.get("patient_context") or {})
        response = post(
            "/api/full-triage",
            {
                "symptoms": case["symptoms"],
                "patient_age": case.get("patient_age"),
                "patient_context": context,
                "language": case.get("language", "en"),
            },
        )
        actual = response["triage"]["triage_level"]
        ok = check(
            f"Scenario {case['scenario_id']}: expected {case['expected_triage_level']}",
            actual == case["expected_triage_level"],
            f"got {actual}",
        )
        all_ok = all_ok and ok
        print(f"       {response['audit']['total_ms']}ms, rule {response['triage']['matched_rule']['rule_id']}")

    return 0 if all_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the MediTriage pipeline.")
    parser.add_argument("--url", help="Verify a deployed backend instead of the local pipeline.")
    args = parser.parse_args()

    exit_code = verify_remote(args.url) if args.url else verify_local()

    section("SUMMARY")
    failures = [item for item in results if item[0] == FAIL]
    print(f"checks run: {len(results)}   passed: {len(results) - len(failures)}   failed: {len(failures)}")
    for _, name, detail in failures:
        print(f"  FAILED: {name}" + (f"  ({detail})" if detail else ""))
    print("\nRESULT:", "ALL CHECKS PASSED" if not failures else f"{len(failures)} CHECK(S) FAILED")
    return exit_code or (1 if failures else 0)


if __name__ == "__main__":
    sys.exit(main())
