# NHIF → SHA mapping

`backend/data/SOURCES.md` (Person 3) refers to this file for the explicit mapping used to
modernise the knowledge base from its pre-October-2024 NHIF draft.

**The change:** the Social Health Insurance Act (2023) replaced the National Hospital Insurance
Fund with the **Social Health Authority (SHA)**, which began operations on **1 October 2024**.
SHA is not a renamed NHIF — it has a different contribution model and a three-fund structure, so
"NHIF" appearing in patient-facing output is a factual error, not a style nit.

---

## Fund structure

| Fund | Code | Covers | Our triage level |
|---|---|---|---|
| Primary Healthcare Fund | **PHF** | Preventive and routine outpatient care at dispensary / health-centre level | `GREEN`, most `YELLOW` |
| Social Health Insurance Fund | **SHIF** | Inpatient, specialist, maternity, chronic and mental-health care | `YELLOW`, and `RED` mental-health crisis |
| Emergency, Chronic and Critical Illness Fund | **ECCIF** | Emergencies, intensive care, major surgery, cancer, dialysis | `RED` |

Contribution: **2.75% of gross household income, minimum KES 300/month** — a flat rate that
replaced NHIF's graduated KES 150–1,700 income bands. Enrolment is mandatory for residents aged 18+.

---

## Field-level mapping in this repository

| NHIF-era draft | Current (SHA) | Where |
|---|---|---|
| `data/nhif_benefits.json` | `data/sha_benefits.json` | renamed; restructured around `funds` + `facility_levels` |
| `"nhif_covered": true` | `"sha_covered": true` | `data/conditions.json` |
| _(no equivalent)_ | `"sha_fund": "PHF …"` | `data/conditions.json` — which fund pays for that condition |
| _(no equivalent)_ | `"sha_fund": "PHF"` | `data/triage_rules.json` — fund emitted with each triage level |
| `"Covered by NHIF (bring card)"` | `"Covered by SHA — <fund name> (bring your SHA card)"` | `agents/care_pathway.py` cost statements |
| `"NHIF: KES 150–1700/month"` | `"SHA: 2.75% of income, minimum KES 300/month"` | `data/sha_benefits.json` → `sha_overview` |
| `"NHIF covers this"` (vague) | `"FREE under the SHA Primary Healthcare Fund"` | patient-facing `cost.statement` |

### Schema shape, before and after

```jsonc
// OLD (do not use): flat list keyed by facility level
{ "benefits": [ { "facility_level": "dispensary", "nhif_covers": true } ] }

// CURRENT: funds are first-class, facility levels reference them by code
{
  "funds": [ { "code": "PHF", "name": "Primary Healthcare Fund", "patient_cost": "...", "covers": [] } ],
  "facility_levels": [ { "level": "dispensary", "sha_fund": "PHF", "patient_cost_kes": "0" } ]
}
```

---

## How this is enforced (not just documented)

| Guard | Location |
|---|---|
| The string `NHIF` never appears in any API response | `backend/tests/test_scenarios.py::test_no_nhif_references_anywhere` |
| No condition may use the legacy `nhif_covered` field | `backend/tests/test_engine.py::test_no_legacy_nhif_fields` |
| Three funds must exist and be the only fund codes | `backend/data/validate_data.py`, `backend/tests/test_engine.py` |
| Every rule and facility level names a valid fund code | `backend/data/validate_data.py` |
| Cost statements name a SHA fund | `backend/tests/test_scenarios.py` |

## Sources

- Social Health Authority — <https://sha.go.ke/> (SHA Paybill 200222)
- Social Health Insurance Act, 2023
- Ministry of Health communications on the SHA rollout (October 2024 onwards)
- Full background: [`docs/plan/SHA_UPDATE_CRITICAL.md`](docs/plan/SHA_UPDATE_CRITICAL.md)

## Caveat carried forward from `SOURCES.md`

Cost figures describe SHA's **stated benefit structure**, not a facility-level audit: some
facilities had implementation gaps during the 2024–2025 transition, and an MoH audit in January
2026 found roughly KES 11 billion in fraudulent claims over that period. The system therefore
states what a fund covers without asserting that a given patient is enrolled.
