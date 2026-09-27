# Architecture Notes and Deviations from the Plan

**Owner:** Person 1 (Lead Developer + DevOps)

The planning documents in `docs/plan/` describe one architecture. This is what
was actually built, why, and where it deliberately differs. Every deviation is
listed with its justification so the team can defend the choices to judges - or
reverse them deliberately.

---

## 1. The central decision: triage does not depend on an LLM

### What the plan said

`TECHNICAL_ARCHITECTURE.md` routed every request through Claude: Agent 1 extracted
symptoms, Agent 2 was described as "Rule-Based" but the sample code used keyword
matching inside Python, and Agent 3 called Claude to phrase the output.

### What was built

Two paths with one output shape:

```
raw symptoms
   |
   +--> deterministic extractor (triage/extractor.py)   ALWAYS RUNS
   |
   +--> LLM extraction (agents/symptom_analyzer.py)     ONLY IF A KEY EXISTS
   |
   v
canonical feature profile          <- canonicalise_profile() merges both
   |
   v
RULE ENGINE (triage/engine.py)     <- decides RED / YELLOW / GREEN. No LLM. Ever.
   |
   v
care pathway (agents/care_pathway.py)  <- SHA costs and actions
   |
   +--> LLM rephrasing (optional)
```

### Why

A demo that depends on an API key, a network connection and available credit can
fail for reasons that have nothing to do with the product. More importantly, an
**urgency level shown to a patient must be reproducible and auditable**. If a
model decides RED vs YELLOW, you cannot explain the decision to a clinician, and
you cannot regression-test it.

So: the LLM proposes structure, the rule engine disposes.

| Concern | Handled by | Guarantee |
|---|---|---|
| Extract symptoms from prose | The LLM, merged with the deterministic extractor | Missing symptoms can only raise acuity |
| Decide RED/YELLOW/GREEN | Rule engine | Same input, same output, forever |
| Phrase the advice | The LLM, falling back to templates | Wording only; content is fixed |
| Cost / SHA fund | `sha_benefits.json` | Never invented by a model |

### Provider choice: why Gemini is the default

The LLM layer (`llm/client.py`) is provider-agnostic: `LLM_PROVIDER` selects
`gemini` (default), `groq`, `ollama`, `anthropic` or `none`. The recommendation
followed from three constraints: the hackathon deadline, the free-tier reality,
and the fact that the product is bilingual.

| Constraint | Gemini (AI Studio) | Groq | Ollama |
|---|---|---|---|
| Free, no credit card | Yes - 500 req/day on flash | Yes, but tight limits | Free (local hardware) |
| Works from Render | Yes - hosted API | Yes - hosted API | **No** - runs on your laptop only |
| Swahili quality | Strongest of the three | Weaker (Llama models) | Weakest |
| JSON output mode | Native `responseMimeType` | `response_format` json_object | `format: json` |

Default model: `gemini-2.5-flash-preview` (10 RPM, 250K TPM, 500 req/day on the
free tier). All request builders are pure functions and unit-tested without a
key or network. Every provider failure degrades to the deterministic path
unless `LLM_MODE=on` demands a model.

### The safety floor

If the profile cannot be analysed at all, `orchestrator.py` floors the result at
YELLOW. An unreadable presentation must never be downgraded to "manage at home".
The default rule (`r999`) is GREEN because most presentations are routine, but
nothing reaches it by accident.

---

## 2. Defects found in the planning documents

These were present in the source documents and are worth knowing about, because
the same errors would have appeared in the build.

| # | Defect | Consequence if built as written | Resolution |
|---|---|---|---|
| 1 | Model ID `claude-opus-5.5` in every sample | First API call fails - the dotted ID does not exist | `CLAUDE_MODEL` env var. Verified current IDs: `claude-haiku-4-5-20251001` (default here), `claude-sonnet-5`, `claude-opus-5-5`, `claude-fable-5-1` |
| 2 | Agent 2's rules could not produce the documented answers - no fever+headache→YELLOW rule, and suicidal ideation was YELLOW in one file and RED in another | 2 of 5 demo scenarios would return the wrong colour | Rule set written and pinned by `tests/test_scenarios.py` |
| 3 | Swahili: fever → "Moto" (heat), diarrhoea → "Kuvimba" (swelling), "Kustay nyumbani" | Judges who speak Swahili catch it immediately | Corrected to *homa* / *kuhara* / *jipatie mapumziko nyumbani*, logged in `swahili_translations.json` |
| 4 | `sha_benefits.json` named `nhif_benefits.json` with `nhif_covers` / `nhif_covered` fields | The "SHA replaced NHIF" update was incomplete - the data layer still spoke NHIF | Renamed and re-schemed; a test asserts `NHIF` never appears in any response |
| 5 | DevOps ownership: Geofry in three files, Person 4 in two others | Two people assume the other is deploying | Person 1 owns backend + deployment, as in `FINAL_TEAM_KICKOFF.md` |
| 6 | "Test case 4 (depression with suicidal ideation)" listed as YELLOW in `TEAM_BRIEF.md`, RED in `TEAM_TASK_BREAKDOWN.md` | Clinically unsafe ambiguity | Treated as RED. Suicidal ideation is a mental health emergency |
| 7 | Demo script shows malaria as YELLOW while the sample rules return GREEN for mild fever | Demo contradicts itself | Rule `r102` (febrile illness needs a malaria test) makes it YELLOW, matching the clinical reasoning |

### Bugs found while building (all fixed, all regression-tested)

These are documented because they were invisible until the code ran, and each
produced a **wrong triage level** - the most expensive failure this system has.

| Bug | Effect | Root cause | Test |
|---|---|---|---|
| Underscore vs prose | Suspected heart attack triaged GREEN | Symptom labels are `chest_pain`; rule keywords are `chest pain`. They could never match | `test_regressions.py::TestBugUnderscoreLabelsNeverMatchedRules` |
| Alias read as top-level keys | Every patient escalated to YELLOW | `features.fever_high` resolved to the whole `features` dict, which is truthy, so `eq: true` matched everyone | `::TestBugNestedAliasReadAsTopLevelKeys` |
| Substring matching | UTI classified as an injury | "often" contains "fall" | `::TestBugSubstringMatchingCausedFalsePositives` |
| Blood pressure as temperature | False fever from `135/85` | Naive numeric extraction | `::TestBugBloodPressureReadAsTemperature` |
| Unquantified fever = high | Child with a 37.5C cold sent to a clinic today | "fever" treated as "high fever" | `::TestBugUnquantifiedFeverTreatedAsHigh` |
| Generic keywords vs narrative | UTI escalated by a wound-care rule | The injury rule's keyword list contained "severe", which matched the patient's sentence | `::TestBugGenericKeywordsMatchedNarrative` |

The lesson worth repeating to judges: a rule engine is only trustworthy if the
text matching underneath it is sound. Six of these seven bugs were in string
matching, not in clinical logic.

---

## 3. Endpoint deviations

The plan specified four endpoints. All four exist with the planned paths. Three
were added:

| Endpoint | Why it was added |
|---|---|
| `GET /` | A judge pasting the bare Render URL should not see a 404 |
| `GET /api/demo/test-cases` | Lets the frontend offer one-click demo buttons, so nobody types under pressure |
| `GET /api/rules` | A clinician can read the entire decision logic without opening Python. This is the strongest answer to "how do you know it is safe?" |
| `POST /api/admin/reload-knowledge-base` | Person 3 can change clinical content without a redeploy. **Unauthenticated** - do not expose in a real deployment |

---

## 4. Data layer deviations

| Plan | Built | Why |
|---|---|---|
| SQLite (`conditions.db`) | JSON files | A hackathon does not need a database. JSON is diffable in git, which means clinical changes are reviewable |
| `nhif_benefits.json` | `sha_benefits.json` with PHF/SHIF/ECCIF | SHA replaced NHIF in October 2024 |
| Free-text `triage_rules.json` samples | Ordered predicate rules with a documented vocabulary | Rules must be machine-evaluable and testable |
| `structured JSON` from the LLM | Same, plus `canonicalise_profile()` | Recomputes numeric features from the source text so prompt drift cannot lower acuity |

### The rule predicate vocabulary

Rules in `data/triage_rules.json` are data, not code. Person 3 can edit them
without touching Python.

```json
{
  "rule_id": "r101",
  "name": "High fever with respiratory symptoms",
  "priority": 101,
  "triage_level": "YELLOW",
  "sha_fund": "PHF",
  "predicates": [
    { "field": "features.fever_high", "eq": true },
    { "field": "symptoms.all", "any": ["cough", "kikohozi", "breathing"] }
  ]
}
```

Operators: `any`, `all`, `none`, `eq`, `not_eq`, `lt`, `lte`, `gt`, `gte`, `exists`.
All predicates must match. Rules are evaluated in ascending `priority`; the first
match wins.

Available field paths:

| Field | Meaning |
|---|---|
| `symptoms.primary` | The most acute extracted symptom |
| `symptoms.all` | All extracted symptoms **plus the raw narrative** |
| `symptoms.labels` | Extracted labels only, no narrative - use this when a rule's second condition is a generic English word |
| `features.fever_present` / `fever_high` / `has_red_flag` / `duration_two_weeks` | Derived booleans |
| `patient.pregnant` / `chronic` / `age` | Patient context |
| `severity`, `duration_days`, `red_flags` | Direct values |

Two invariants are enforced by tests:

1. Every field a rule references must be resolvable by the engine.
2. **No RED rule may be evaluated after any non-RED rule.** Acuity cannot be shadowed.

---

## 5. What is deliberately NOT built

Honesty about scope is part of the pitch.

| Item | Status | Reason |
|---|---|---|
| Agent 4 (Outcome Tracker) | Not built | The plan itself says skip it for the MVP |
| NVIDIA Brev | Not used | No embeddings, no GPU workload. See `DEPLOYMENT.md` for the honest framing |
| USSD / SMS fallback | Not built | Mentioned in the plan as pseudocode. A real USSD gateway needs an aggregator agreement and a shortcode |
| Swahili LLM output | Template Swahili only | Template Swahili is reviewed and correct. Generated Swahili is not, without a native-speaking clinician |
| Authentication | None | Out of scope for a demo. **Required before any pilot** - health data is sensitive |
| Persistence / audit log | None | Nothing is stored. For a pilot this becomes a legal requirement, not a feature |
| Real clinic integration | None | No KHIS or Taifa Care integration exists |

### Regulatory and safety posture

This is a prototype and the repository says so:

* `clinical_reviewed: false` on all 10 conditions
* A `PILOT_TODO` list in `triage_rules.json`
* Every response carries a "guidance only, not a diagnosis" disclaimer
* The system never names a definitive diagnosis
* Output is guidance about **urgency and next steps**, not treatment

Before any real patient contact this needs: clinician sign-off on the rules, a
native-speaker review of the Swahili, data-protection compliance under Kenya's
Data Protection Act 2019, and registration through the Kenya Digital Health
Agency sandbox.

---

## 6. Testing strategy

`backend/tests/` - 158 tests, no network, no API key.

| File | Covers |
|---|---|
| `test_scenarios.py` | The demo contract: all 5 scenarios, their pathways, SHA funds, SLA, absence of NHIF |
| `test_regressions.py` | Every bug in the table above, one test class each |
| `test_extractor.py` | Temperature, duration, blood pressure, symptoms, red flags, Swahili, canonicalisation |
| `test_engine.py` | Predicates, path resolution, ruleset integrity, knowledge base content |
| `test_api.py` | Every endpoint, response shape, validation errors, determinism, latency |

`verify.py` is the dependency-free equivalent, and doubles as a remote checker:

```bash
python verify.py                                  # local pipeline
python verify.py --url https://your-app.onrender.com   # deployed service
```

Why both: pytest is for development, `verify.py` is for the demo laptop and for
checking a live deployment. The scenario contract is asserted in both, so a
regression fails loudly either way.

---

## 7. Performance

| Path | Measured |
|---|---|
| Agent 1 deterministic extraction | 1-3 ms |
| Agent 2 rule evaluation (26 rules) | <1 ms |
| Agent 3 template pathway | 1-5 ms |
| **Full pipeline, `LLM_MODE=off`** | **5-17 ms end to end** |
| Full pipeline with one LLM call | typically 2-6 s |

The 30-second requirement in the plan is met by three orders of magnitude on the
deterministic path. `audit.within_sla` is returned on every response so the claim
is measured rather than assumed.

Note the honest version for judges: the ms figure is the rules path. With an LLM
enabled you are waiting on a network call, which is why `LLM_MODE=off` is the
recommended setting on demo day.
