/**
 * Integration test: does the frontend's adapter survive REAL backend responses?
 *
 * Why this exists
 * ---------------
 * The frontend was written against an assumed API contract. Three field names
 * were wrong (`personalized_instruction`, `location`, `cost`), and two of them
 * returned OBJECTS that React cannot render - that blanked the results page at
 * runtime while `next build` still passed, because the failure only happens
 * when real data flows through.
 *
 * This script closes that gap without a browser: it fetches live responses from
 * the FastAPI backend, runs them through the frontend's own
 * `normalizeTriageResult`, and asserts every value the UI renders is a string
 * or an array of strings.
 *
 * Usage (backend must be running):
 *   node scripts/verify-api-contract.mjs
 *   node scripts/verify-api-contract.mjs http://localhost:8000
 *
 * Exit code 0 = all scenarios renderable. Non-zero = a field would crash the UI.
 */
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";

const API = (process.argv[2] || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

// formatOutput.js is ESM but the repo has no "type":"module" (Next.js needs
// CommonJS there), so load its exact source through a temporary .mjs module.
const SOURCE = new URL("../src/utils/formatOutput.js", import.meta.url);
const TEMP = new URL("../src/utils/__contract_check.tmp.mjs", import.meta.url);

let failures = 0;
let checks = 0;

function check(name, ok, detail = "") {
  checks += 1;
  if (ok) {
    console.log(`  ok    ${name}`);
  } else {
    failures += 1;
    console.log(`  FAIL  ${name}${detail ? `  -> ${detail}` : ""}`);
  }
}

function isRenderable(value) {
  if (typeof value === "string") return true;
  if (typeof value === "number" || typeof value === "boolean") return true;
  if (value === null || value === undefined) return true;
  return false; // arrays of strings AND plain objects would both fail here
}

function isStringArray(value) {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

async function main() {
  writeFileSync(TEMP, readFileSync(SOURCE));
  const { normalizeTriageResult, getTriageMeta } = await import(TEMP.href);

  console.log(`\nBackend: ${API}\n${"=".repeat(70)}`);

  let health;
  try {
    health = await (await fetch(`${API}/health`)).json();
  } catch (err) {
    console.error(`\nCannot reach the backend at ${API}.\nStart it with:  cd backend && uvicorn main:app --reload\n`);
    unlinkSync(TEMP);
    process.exit(2);
  }
  console.log(`health: ${health.status}, knowledge base: ${JSON.stringify(health.knowledge_base)}\n`);

  const { test_cases: cases } = await (await fetch(`${API}/api/demo/test-cases`)).json();
  check("5 demo scenarios available", cases.length === 5, `got ${cases.length}`);

  const FALLBACK_INSTRUCTION = "Please see a health worker for next steps.";

  for (const demo of cases) {
    console.log(`\n--- Scenario ${demo.scenario_id}: ${demo.patient_name} (expect ${demo.expected_triage_level}) ---`);

    const response = await fetch(`${API}/api/full-triage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symptoms: demo.symptoms,
        patient_age: demo.patient_age,
        patient_context: demo.patient_context || {},
        language: demo.language || "en",
      }),
    });

    if (!response.ok) {
      check("request accepted", false, `HTTP ${response.status}`);
      continue;
    }

    const payload = await response.json();
    const r = normalizeTriageResult(payload);

    // 1. Every field the components render must be React-renderable.
    for (const field of ["triageLevel", "urgency", "rationale", "instruction", "location", "cost", "shaFund", "disclaimer"]) {
      check(`${field} is a renderable string`, isRenderable(r[field]), `typeof ${typeof r[field]} (${JSON.stringify(r[field])})`);
    }
    check("whatToBring is a string[]", isStringArray(r.whatToBring), JSON.stringify(r.whatToBring));
    check("dangerSigns is a string[]", isStringArray(r.dangerSigns), JSON.stringify(r.dangerSigns));

    // 2. Content that must actually be present, not silently defaulted.
    check("triage level matches expected", r.triageLevel === demo.expected_triage_level, `got ${r.triageLevel}`);
    check("triage meta resolves to a CSS class", !!getTriageMeta(r.triageLevel).className);
    check(
      "instruction is the real backend text (not the fallback)",
      r.instruction !== FALLBACK_INSTRUCTION && r.instruction.length > 10,
      r.instruction
    );
    check("location is the facility name", !!r.location && !r.location.includes("[object"), r.location);
    check("cost is the cost statement", !!r.cost && !r.cost.includes("[object"), r.cost);
    check("danger signs present", r.dangerSigns.length > 0, `${r.dangerSigns.length} signs`);
    check("no legacy NHIF wording", !JSON.stringify(payload).toLowerCase().includes("nhif"));

    console.log(`        level=${r.triageLevel}  fund=${r.shaFund}  where=${r.location}`);
    console.log(`        instruction: ${r.instruction.slice(0, 95)}`);
    console.log(`        cost: ${r.cost.slice(0, 95)}`);
  }

  unlinkSync(TEMP);

  console.log(`\n${"=".repeat(70)}`);
  console.log(`checks: ${checks}   failed: ${failures}`);
  console.log(failures === 0 ? "RESULT: frontend adapter handles every live response" : "RESULT: FAILED");
  // Set exitCode rather than calling process.exit(): an immediate exit while
  // fetch handles are still closing trips a libuv assertion on Windows.
  process.exitCode = failures === 0 ? 0 : 1;
}

main().catch((err) => {
  try { unlinkSync(TEMP); } catch (_) {}
  console.error("\nUnexpected error:", err);
  process.exitCode = 1;
});
