# MediTriage AI

**Smart healthcare triage for Kenya's Primary Care Network.**

A patient or health worker describes symptoms. The system returns **RED** (emergency - hospital now),
**YELLOW** (urgent - clinic today) or **GREEN** (routine - manage at home), together with the care
pathway, the **SHA** fund that covers it, and a printable referral slip.

> **Status:** backend complete and verified against all 5 demo scenarios.
> Frontend is a scaffold that Person 2 owns. Clinical content is seeded and **awaiting clinician sign-off**.

---

## Repository layout

```
MediTriage-AI/
├── backend/                     # Person 1 - FastAPI service
│   ├── main.py                  # App entry point + error handling
│   ├── orchestrator.py          # Chains the 3 agents, times the run
│   ├── config.py                # Environment settings
│   ├── agents/
│   │   ├── symptom_analyzer.py  # Agent 1 - LLM + deterministic extractor
│   │   ├── triage_router.py     # Agent 2 - rule engine, never an LLM
│   │   └── care_pathway.py      # Agent 3 - SHA costs, instructions
│   ├── triage/
│   │   ├── extractor.py         # Bilingual keyword/regex feature extraction
│   │   └── engine.py            # Predicate rule engine
│   ├── llm/client.py            # Optional Anthropic wrapper (never raises)
│   ├── knowledge/loader.py      # Reads data/*.json
│   ├── data/                    # Person 3 - the knowledge base
│   │   ├── conditions.json      # 10 Kenyan conditions
│   │   ├── triage_rules.json    # RED/YELLOW/GREEN decision rules
│   │   ├── sha_benefits.json    # PHF / SHIF / ECCIF coverage
│   │   ├── swahili_translations.json
│   │   └── test_cases.json      # The 5 demo scenarios + regression cases
│   ├── tests/                   # 90+ tests, no network required
│   └── requirements.txt
├── frontend/                    # Person 2 - Next.js (currently a scaffold)
├── render.yaml                  # Render blueprint for the backend
└── docs/
    ├── DEPLOYMENT.md            # Live URLs + deploy steps
    ├── API_DOCS.md              # Endpoint reference for Person 2
    └── ARCHITECTURE_NOTES.md    # Design decisions + deviations from the plan
```

---

## Quick start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Open <http://localhost:8000/docs> for interactive API documentation.

No API key is needed. Without one the service runs in deterministic
mode and all three triage levels still work correctly. Add a free Gemini key
(https://aistudio.google.com/apikey) to enable AI structuring and phrasing.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open <http://localhost:3000>.

### Tests

```bash
cd backend
python -m pytest tests/ -v
```

The suite forces `LLM_MODE=off`, so it never touches the network.

---

## The two-path design (read this before changing anything)

The original plan sent every request through an LLM. That makes a live demo depend
on an API key, a network connection and available credit. This build inverts it:

| Path | Runs when | Decides triage? |
|---|---|---|
| **Deterministic rule engine** (`triage/engine.py` + `data/triage_rules.json`) | **Always** | **Yes - always** |
| **LLM** (Agent 1 extraction, Agent 3 phrasing) | Only if `LLM_PROVIDER` is configured and `LLM_MODE` allows | **No** |

Consequences:

* A model outage, an expired key or a dead network **cannot change** a RED/YELLOW/GREEN decision.
  It can only change how warmly the advice is worded.
* The LLM proposes structure; Agent 2 disposes. Both paths feed the same canonical profile,
  and `triage/extractor.py::canonicalise_profile` recomputes the numeric features and the
  red-flag union, so prompt drift cannot lower an acuity level.
* When the profile cannot be analysed at all, the orchestrator applies a **safety floor** of
  YELLOW - an unreadable presentation is never downgraded to GREEN.

### LLM providers

The LLM layer is provider-agnostic. `LLM_PROVIDER` selects one:

| Provider | API key | Hosted? | Free tier | Swahili | Use it for |
|---|---|---|---|---|---|
| **`gemini`** (default) | `GEMINI_API_KEY` | Yes - works from Render | 500 req/day, no credit card | **Strongest of the free options** | **The hackathon demo** |
| `groq` | `GROQ_API_KEY` | Yes | Tight rate limits | Weaker (Llama models) | Fallback provider |
| `ollama` | none | No - local machine only | Local hardware | Weakest | Offline recorded demo |
| `anthropic` | `ANTHROPIC_API_KEY` | Yes | Paid only | Strong | If you already have a key |
| `none` | none | - | - | - | Fully deterministic |

Gemini is the recommended default: the free AI Studio key needs no billing
details, the API is hosted so Render works like local, and it handles Swahili
far better than the other free options - important because the app is bilingual
by design. Model IDs are configurable (`LLM_MODEL`); the default is
`gemini-2.5-flash-preview`.

### LLM modes

| `LLM_MODE` | Behaviour |
|---|---|
| `auto` (default) | Use the configured LLM if its key is present, otherwise deterministic |
| `off` | Never call any LLM. **Safest setting on demo day.** |
| `on` | Require the LLM; raise if it is unreachable |

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + configuration check (Render polls this) |
| `GET` | `/` | Landing payload, so a bare URL is not a 404 |
| `POST` | `/api/analyze-symptoms` | Agent 1 only |
| `POST` | `/api/triage-decision` | Agent 2 only |
| `POST` | `/api/care-pathway` | Agent 3 only |
| `POST` | `/api/full-triage` | The chained pipeline the frontend uses |
| `GET` | `/api/demo/test-cases` | The 5 demo scenarios, for one-click demos |
| `GET` | `/api/rules` | The rule set, for clinician review |
| `POST` | `/api/admin/reload-knowledge-base` | Re-read `data/*.json` without a redeploy |

Full request/response shapes: [`docs/API_DOCS.md`](docs/API_DOCS.md).

---

## The 5 demo scenarios

| # | Scenario | Age | Expected | SHA fund |
|---|---|---|---|---|
| 1 | Malaria suspicion - fever, chills, headache | 25 | **YELLOW** | PHF |
| 2 | Routine hypertension review, 135/85 | 55 | **GREEN** | PHF |
| 3 | Severe chest pain with breathlessness | 52 | **RED** | ECCIF |
| 4 | Depression with suicidal ideation | 28 | **RED** | SHIF |
| 5 | Child with common cold, 37.5C | 8 | **GREEN** | PHF |

`backend/tests/test_scenarios.py` enforces every one of these. If a rule or prompt change
alters any level, the suite fails with an explanation.

---

## Clinical safety posture

This is a hackathon prototype, and the repository should not pretend otherwise.

* `clinical_reviewed: false` on every condition. No clinician has signed off yet.
* `triage_rules.json` carries a `PILOT_TODO` list of what must be validated before real use.
* Every output carries a "guidance only, not a diagnosis" disclaimer.
* The system never names a definitive diagnosis; it reports findings and urgency.
* Rules are ordered so that **no RED rule can be shadowed** by a YELLOW or GREEN rule -
  asserted by a test.

---

## SHA, not NHIF

NHIF was replaced by the **Social Health Authority (SHA)** in October 2024. All cost
statements name one of SHA's three funds:

* **PHF** - Primary Healthcare Fund: free routine care at dispensary/health-centre level
* **SHIF** - Social Health Insurance Fund: inpatient and specialist care
* **ECCIF** - Emergency, Chronic and Critical Illness Fund: emergencies and catastrophic care

A test asserts that the string `NHIF` never appears in any API response.

---

## Team ownership

| Person | Role | Owns |
|---|---|---|
| **1** | Lead Developer + DevOps | `backend/` code, `render.yaml`, CI/deploy, `docs/DEPLOYMENT.md` |
| **2** | Frontend Developer | `frontend/` UI, referral slip design |
| **3** | Data & Content Specialist | `backend/data/*.json` clinical content |
| **4** | Clinical/Product Researcher | validation docs, clinic workflow, pilot roadmap |

Person 3 can change clinical logic **without touching Python** - edit
`backend/data/triage_rules.json` and run `python -m pytest tests/`.
