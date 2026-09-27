# MediTriage AI - API Reference

Base URL (local): `http://localhost:8000`
Base URL (deployed): `https://medi-triage-backend.onrender.com`

Interactive docs: `/docs` (Swagger UI) and `/redoc`.

**Owner:** Person 1 (Lead Developer + DevOps)
**Consumer:** Person 2 (Frontend Developer)

---

## Deployment status of each field

Every triage decision comes from a deterministic rule engine. The LLM (Gemini by
default) is optional - see `README.md` for the two-path design and provider table.

---

## `GET /health`

Liveness and configuration. Render polls this to decide whether the service is up.

```json
{
  "status": "ok",
  "service": "MediTriage AI",
  "version": "0.1.0",
  "llm": {
    "enabled": false,
    "mode": "auto",
    "provider": "gemini",
    "model": null,
    "reason": "GEMINI_API_KEY not set - running in deterministic offline mode",
    "last_error": null,
    "working": false
  },
  "knowledge_base": {
    "conditions": 10,
    "rules": 26,
    "demo_scenarios": 5,
    "regression_cases": 5,
    "sha_funds": 3,
    "swahili_symptoms": 37,
    "source_dir": "backend/data"
  },
  "checks": {
    "knowledge_base_loaded": true,
    "demo_scenarios_present": true,
    "sha_benefits_present": true,
    "llm_configured": false
  }
}
```

`status` is `"ok"` when the knowledge base loaded, `"degraded"` otherwise.
Use `checks` to decide whether the demo is safe to run.

> **`llm.enabled` means "configured", not "working".** A wrong or expired key still reports
> `enabled: true` while every request quietly falls back to the deterministic engine. Check
> `llm.working` / `llm.last_error`, or call `/api/admin/llm-check` below.

---

## `POST /api/full-triage`

The endpoint the frontend should call. Chains all three agents.

### Request

```json
{
  "symptoms": "I have been having high fever for 2 days, with chills, severe headache, and my whole body aches. I also feel nauseous.",
  "patient_age": 25,
  "language": "en",
  "sex": "female",
  "patient_context": {
    "hiv_status": "negative",
    "pregnant": false,
    "chronic_conditions": [],
    "location": "Kisumu"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `symptoms` | string | yes | 3-2000 chars. English, Swahili or mixed. |
| `patient_age` | int or null | no | 0-120 |
| `language` | `"en"` or `"sw"` | no | Defaults to `"en"` |
| `sex` | string or null | no | |
| `patient_context.pregnant` | bool | no | Default `false`. Changes triage risk. |
| `patient_context.chronic_conditions` | string[] | no | e.g. `["hypertension","diabetes"]` |
| `patient_context.hiv_status` | string | no | |
| `patient_context.location` | string | no | County name, used in wording only |

### Response `200`

```json
{
  "triage": {
    "triage_level": "YELLOW",
    "urgency": "URGENT",
    "rationale": "Fever with headache, chills and body aches is a febrile illness. In Kenya malaria and typhoid must be excluded with a test - this needs a same-day clinic visit.",
    "recommended_pathway": "clinic",
    "sha_fund": "PHF",
    "matched_rule": { "rule_id": "r102", "name": "Febrile illness - malaria or typhoid must be excluded" },
    "colour": "#f9a825",
    "label_en": "URGENT - go to the clinic today",
    "label_sw": "HARAKA - nenda kliniki leo",
    "target_time": "within 24 hours",
    "engine": "deterministic-rules-v1",
    "alternatives": [],
    "confidence": 0.6,
    "explanation": [
      "Matched rule r102: Febrile illness - malaria or typhoid must be excluded",
      "Fever with headache, chills and body aches is a febrile illness...",
      "SHA fund applicable: PHF"
    ],
    "agent": "triage_router",
    "rules_evaluated": 22,
    "patient_summary": "fever, with chills, headache, body aches, for 2 day(s), severity moderate."
  },
  "symptom_analysis": {
    "primary_symptom": "fever",
    "associated_symptoms": ["chills", "headache", "body_aches"],
    "all_symptoms": ["fever", "chills", "headache", "body_aches", "nausea"],
    "duration_days": 2,
    "severity": "moderate",
    "red_flags": [],
    "features": {
      "temperature_celsius": null,
      "fever_present": true,
      "fever_high": false,
      "fever_unquantified": true,
      "has_red_flag": false,
      "red_flag_count": 0,
      "duration_two_weeks": false
    },
    "patient": { "age": 25, "pregnant": false, "chronic": [], "hiv_status": "negative" },
    "extraction_method": "deterministic",
    "extraction_confidence": 0.6,
    "llm_used": false
  },
  "care_pathway": {
    "triage_level": "YELLOW",
    "language": "en",
    "headline": "URGENT - go to the clinic today",
    "patient_instruction": "Go to the nearest health centre or clinic today. Bring your SHA card or ID. Drink fluids and rest while you wait to be seen.",
    "instruction_source": "template",
    "actions": ["Go to the nearest health centre or clinic today.", "..."],
    "facility": {
      "level": "health_centre",
      "name": "Nearest health centre",
      "services": ["Consultation", "Laboratory tests", "Injections", "Maternity care", "Minor procedures", "Counselling"]
    },
    "sha": {
      "code": "PHF",
      "fund_code": "PHF",
      "name": "Primary Healthcare Fund",
      "covers": ["Outpatient consultation", "..."],
      "patient_cost": "KES 0 at dispensary and health centre level; transport is the patient's only cost"
    },
    "cost": {
      "statement": "This is free at a dispensary or health centre under the SHA Primary Healthcare Fund. You pay only transport.",
      "statement_en": "...",
      "statement_sw": "...",
      "patient_pays_kes": "0"
    },
    "what_to_bring": ["SHA card or ID", "Any medicines you are already taking"],
    "danger_signs_to_watch": ["Confusion or drowsiness", "Difficulty breathing", "Convulsions"],
    "follow_up": "If you cannot reach a clinic today, go first thing tomorrow morning.",
    "possible_condition": "Malaria",
    "condition_slug": "malaria",
    "clinical_reviewed": false,
    "disclaimer": "This is guidance only, not a diagnosis. A health worker will examine you."
  },
  "audit": {
    "requested_at": "2026-09-27T10:15:00+00:00",
    "total_ms": 6,
    "sla_seconds": 30.0,
    "within_sla": true,
    "steps": [
      { "step": "agent_1_symptom_analyzer", "ms": 2, "ok": true },
      { "step": "agent_2_triage_router", "ms": 1, "ok": true },
      { "step": "agent_3_care_pathway", "ms": 2, "ok": true }
    ],
    "degraded_components": [],
    "llm": { "enabled": false, "mode": "auto", "model": null, "reason": "..." },
    "knowledge_base": { "...": "..." },
    "deterministic_core": true
  }
}
```

### Fields the frontend actually needs

| Purpose | Field |
|---|---|
| Banner colour | `triage.colour` |
| Banner text | `triage.triage_level` + `triage.urgency` |
| Why | `triage.rationale`, `triage.explanation[]` |
| What to do | `care_pathway.patient_instruction`, `care_pathway.actions[]` |
| Where | `care_pathway.facility.name` |
| Cost | `care_pathway.cost.statement`, `care_pathway.sha.fund_code` |
| Bring | `care_pathway.what_to_bring[]` |
| Watch for | `care_pathway.danger_signs_to_watch[]` |
| Small print | `care_pathway.disclaimer` |
| Demo confidence | `audit.total_ms`, `audit.within_sla` |

### Errors

`422` - validation problem:

```json
{
  "error": "invalid_request",
  "message": "Some of the information sent was not valid.",
  "problems": [{ "field": "patient_age", "message": "Input should be less than or equal to 120" }]
}
```

`500` - `{ "error": "internal_error", "message": "..." }`. Stack traces are never returned.

---

## `POST /api/analyze-symptoms`

Agent 1 alone. Same request body as `/api/full-triage`. Returns the
`symptom_analysis` object directly. Useful for debugging extraction.

## `POST /api/triage-decision`

Agent 2 alone - useful for testing rule changes without a full pipeline run.

```json
{ "symptom_profile": { "primary_symptom": "chest_pain", "all_symptoms": ["chest_pain", "difficulty_breathing"], "red_flags": [], "features": {} } }
```

Returns the `triage` object. `422` if `symptom_profile` is empty.

## `POST /api/care-pathway`

Agent 3 alone.

```json
{ "triage_level": "RED", "symptom_profile": { "primary_symptom": "chest_pain" }, "language": "en" }
```

## `GET /api/demo/test-cases`

The 5 demo scenarios plus the regression cases. Use this to build one-click demo
buttons so nobody has to type during judging.

## `GET /api/rules`

The full rule set with predicates and rationales, for clinician review.

## `POST /api/admin/reload-knowledge-base`

Re-reads `backend/data/*.json` without a redeploy. Person 3 can iterate on content
and reload. **There is no authentication on this endpoint** - do not expose it to
patients in a real deployment.

## `GET /api/admin/llm-check`

Makes one small live call to the configured LLM provider and reports exactly what happened,
including the provider's own error text.

```json
{
  "provider": "gemini",
  "model": "gemini-2.5-flash-preview",
  "mode": "auto",
  "configured": true,
  "reason": "gemini enabled (gemini-2.5-flash-preview)",
  "ok": false,
  "sample": null,
  "error": "gemini call failed (RuntimeError): HTTP 400 from https://generativelanguage.googleapis.com/...: {\"error\": {\"code\": 400, \"message\": \"API key not valid. Please pass a valid API key.\", \"status\": \"INVALID_ARGUMENT\", ...}}",
  "last_error": {
    "provider": "gemini",
    "at": "2026-09-27T15:04:11+00:00",
    "message": "gemini call failed (RuntimeError): HTTP 400 ..."
  }
}
```

**Why this exists.** Because a broken key is invisible at the product level: triage still returns
the correct RED/YELLOW/GREEN from the rule engine. On a deployed service the real reason only
appears in the server log, so this endpoint brings it into the open. Common readings:

| `error` contains | Meaning | Fix |
|---|---|---|
| `API key not valid` (400) | Key wrong, revoked, or from another project | Regenerate at the provider console |
| `model not found` / 404 | `LLM_MODEL` is wrong for this provider | Try an alternative model ID |
| `429` / `quota` | Free-tier rate limit or daily cap | Wait, or switch `LLM_PROVIDER` |
| connection/timeout | Network, or Ollama not running | Check the host; `ollama serve` locally |

Equivalent locally: `cd backend && python check_llm.py`. **Unauthenticated** - as with the
reload endpoint, do not expose these admin routes in a real deployment.

---

## curl examples

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/full-triage \
  -H "Content-Type: application/json" \
  -d '{"symptoms":"severe chest pain and I cannot breathe, I am sweating","patient_age":52}'

curl -X POST http://localhost:8000/api/full-triage \
  -H "Content-Type: application/json" \
  -d '{"symptoms":"Nina homa kali, maumivu ya kichwa na maumivu ya mwili kwa siku tatu.","patient_age":30,"language":"sw"}'

curl http://localhost:8000/api/demo/test-cases
```

---

## CORS

Configured from `CORS_ORIGINS`. Default:
`http://localhost:3000,http://127.0.0.1:3000`

**Add your Vercel URL before the demo**, or the browser will block every request:

```
CORS_ORIGINS=http://localhost:3000,https://medi-triage.vercel.app
```
