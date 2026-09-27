# AGENT.md — MediTriage AI integration contract

This is the shared contract between the frontend and the backend. If you are
editing either side, this file is the source of truth. Full reference:
`docs/API_DOCS.md`. Deployment: `docs/DEPLOYMENT.md`.

---

## The API contract (frontend must match this exactly)

`POST /api/full-triage` — the endpoint the intake form calls.

**Request**

```json
{
  "symptoms": "I have had a high fever for 2 days with chills and headache",
  "patient_age": 25,
  "language": "en",
  "patient_context": {
    "pregnant": false,
    "hiv_status": "negative",
    "chronic_conditions": ["hypertension"],
    "location": "Kisumu"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `symptoms` | string | Required, 3-2000 chars. English, Swahili or mixed. |
| `patient_age` | int or null | 0-120 |
| `language` | `"en"` or `"sw"` | Defaults to `"en"` |
| `patient_context.pregnant` | bool | Changes triage risk |
| `patient_context.hiv_status` | string | `"positive"` / `"negative"` / `"unknown"` |
| `patient_context.chronic_conditions` | string[] | `["hypertension"]`, `["diabetes"]`, `["asthma"]` |

> **Careful:** the API expects `hiv_status` (a string) and `chronic_conditions`
> (an array). Unknown keys are silently ignored by the API, so a typo means the
> triage loses that risk signal without any error being raised.

**Response (only the fields the UI needs)**

```json
{
  "triage": {
    "triage_level": "YELLOW",
    "urgency": "URGENT",
    "rationale": "Fever with headache, chills and body aches is a febrile illness...",
    "recommended_pathway": "clinic",
    "sha_fund": "PHF",
    "colour": "#f9a825",
    "matched_rule": { "rule_id": "r102", "name": "Febrile illness..." }
  },
  "care_pathway": {
    "patient_instruction": "Go to the nearest health centre or clinic today. ...",
    "actions": ["Go to the nearest health centre or clinic today.", "..."],
    "facility": { "level": "health_centre", "name": "Nearest health centre", "services": [] },
    "sha": { "fund_code": "PHF", "name": "Primary Healthcare Fund", "covers": [] },
    "cost": {
      "statement": "This is free at a dispensary or health centre under the SHA Primary Healthcare Fund.",
      "patient_pays_kes": "0"
    },
    "what_to_bring": ["SHA card or ID", "Any medicines you are already taking"],
    "danger_signs_to_watch": ["Confusion or drowsiness", "Difficulty breathing"],
    "follow_up": "If you cannot reach a clinic today, go first thing tomorrow morning.",
    "disclaimer": "This is guidance only, not a diagnosis. A health worker will examine you."
  },
  "symptom_analysis": { "primary_symptom": "fever", "extraction_method": "deterministic" },
  "audit": { "total_ms": 12, "within_sla": true, "llm": { "enabled": false, "provider": "gemini" } }
}
```

### The three fields that bite

These are objects, not strings. Rendering them directly throws
*"Objects are not valid as a React child"* and blanks the page:

| Field | Use this instead |
|---|---|
| `care_pathway.facility` | `care_pathway.facility.name` |
| `care_pathway.cost` | `care_pathway.cost.statement` |
| `care_pathway.sha` | `care_pathway.sha.fund_code` |

`frontend/src/utils/formatOutput.js` (`normalizeTriageResult`) flattens all of
this and coerces anything unexpected to a string. **Render only its output.**

---

## Triage levels

| Level | Meaning | Colour | Typical pathway |
|---|---|---|---|
| `RED` | Emergency - hospital now | `#d32f2f` | hospital (ECCIF) |
| `YELLOW` | Urgent - clinic today | `#f9a825` | clinic (PHF) |
| `GREEN` | Routine - manage at home | `#2e7d32` | home / routine visit (PHF) |

The backend decides these with a **deterministic rule engine**. An AI model
(Gemini by default) only structures symptoms and phrases the advice - it can
never change the level. See `README.md`.

---

## Folder structure

```
frontend/
├── src/
│   ├── pages/          # Next.js pages router: index, intake, results, demo
│   ├── components/     # IntakeForm, TriageResult, ReferralSlip
│   ├── utils/          # api-client.js (fetch), formatOutput.js (adapters)
│   ├── api/            # thin re-export barrels
│   └── styles/         # colors.css (tokens) + mobile-first.css
├── package.json
└── .env.local.example  # NEXT_PUBLIC_API_URL
```

## Design rules

1. **Mobile-first.** Primary target is a phone at a clinic.
2. **Never invent clinical advice in the frontend.** Render what the API returns.
3. **Colour-code by level only.** RED/YELLOW/GREEN are fixed tokens.
4. **The referral slip must print cleanly** on one page (`no-print` class).
5. **Say SHA, never NHIF.** NHIF was replaced in October 2024.

## Running locally

```bash
# terminal 1 - backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# terminal 2 - frontend
cd frontend && npm install && cp .env.local.example .env.local && npm run dev
```

## Verifying the integration

With the backend running:

```bash
cd frontend && node scripts/verify-api-contract.mjs
```

It pushes all 5 demo scenarios through `normalizeTriageResult` and fails if any
field would render as an object - the exact bug class that `next build` cannot
catch, because it only appears with real data.
