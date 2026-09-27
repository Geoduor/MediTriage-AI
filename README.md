# MediTriage AI 🏥

**Smart healthcare triage for Kenya's Primary Care Network** — a system that listens to patient
symptoms and instantly tells a health worker whether the patient needs a hospital (🔴 **RED**),
urgent clinic care (🟡 **YELLOW**), or routine treatment (🟢 **GREEN**), with the care pathway and
the **SHA** fund that covers it.

Built at the GOMYCODE *Come Build with AI* Hackathon, 27 September 2026.

| | |
|---|---|
| Frontend | Next.js on Vercel — set `NEXT_PUBLIC_API_URL` to your Render URL |
| Backend | FastAPI on Render — see `render.yaml` and `docs/DEPLOYMENT.md` |
| Source | this repository (`backend/` + `frontend/`) |

> **Status.** Backend and frontend are integrated and verified. Clinical content is seeded and
> **awaiting clinician sign-off** (`clinical_reviewed: false` on every condition).

---

## 🩺 The problem

Kenya's primary-care clinics see 50–80+ patients a day, and triage is largely done by gut feel:

- Urgent cases (severe malaria, chest pain) sometimes wait behind routine check-ups.
- Routine cases get referred to hospitals unnecessarily, costing patients time and money.
- Telemedicine is growing, but nothing standardises the triage of symptoms called or messaged in.

## 💡 The solution

MediTriage AI triages in **seconds**, from home or at the clinic:

- Bilingual — understands **English and Swahili**
- Covers Kenya's **10 most common primary-care conditions** (malaria, respiratory infection,
  hypertension, diarrhoea, chest pain, depression/anxiety, UTI, skin infection, diabetes, injury)
- Explains cost under Kenya's **SHA** three-fund system (PHF / SHIF / ECCIF), which replaced NHIF
  in October 2024
- Produces a **printable referral slip** in plain language, with danger signs to watch for
- Works with **no AI provider configured at all** — see "two-path design" below

---

## 🖥️ How it works

```
PATIENT (at home or at the clinic)
   ↓  describes symptoms in their own words (English or Swahili)
Agent 1  Symptom Analyzer   → structures symptoms, severity, red flags
   ↓
Agent 2  Triage Router      → decides RED / YELLOW / GREEN   ← deterministic rule engine
   ↓
Agent 3  Care Pathway       → where to go, what to bring, what it costs
   ↓
patient / nurse gets a clear, printable result
```

---

## The two-path design (read this before changing anything)

The original plan sent every request through an LLM. That makes a live demo depend on an API key,
a network connection and available credit. This build inverts it:

| Path | Runs when | Decides triage? |
|---|---|---|
| **Deterministic rule engine** (`triage/engine.py` + `data/triage_rules.json`) | **Always** | **Yes — always** |
| **LLM** (Agent 1 extraction, Agent 3 phrasing) | Only if `LLM_PROVIDER` is configured and `LLM_MODE` allows | **No** |

Consequences:

- A model outage, an expired key or a dead network **cannot change** a RED/YELLOW/GREEN decision.
  It can only change how warmly the advice is worded.
- The LLM proposes structure; Agent 2 disposes. Both paths feed the same canonical profile, and
  `triage/extractor.py::canonicalise_profile` recomputes the numeric features and the red-flag
  union, so prompt drift cannot lower an acuity level.
- When a profile cannot be analysed at all, the orchestrator applies a **safety floor** of YELLOW —
  an unreadable presentation is never downgraded to GREEN.

### LLM providers

`LLM_PROVIDER` selects one; the LLM is always optional.

| Provider | Key | Hosted? | Free tier | Notes |
|---|---|---|---|---|
| **`gemini`** (default) | `GEMINI_API_KEY` | Yes | 500 req/day, no card | Strongest Swahili; recommended |
| `groq` | `GROQ_API_KEY` | Yes | Tight rate limits | Fast fallback |
| `ollama` | none | No — local only | Local hardware | Offline demo only; cannot serve Render |
| `anthropic` | `ANTHROPIC_API_KEY` | Yes | Paid | Claude |
| `none` | none | — | — | Fully deterministic |

`LLM_MODE`: `auto` (default, use the LLM if a key exists) · `off` (never call one — safest on demo
day) · `on` (require one).

### NVIDIA Brev

Not used, and not needed. Judging is tool-neutral, and this workload is a rules engine plus two
short LLM calls with no embeddings — GPU compute would add latency and deployment risk for no
functional gain. See `docs/DEPLOYMENT.md` for the honest framing.

---

## 📁 Repository layout

```
MediTriage-AI/
├── backend/                     # FastAPI service
│   ├── main.py                  # App entry point, error handling, lifespan checks
│   ├── orchestrator.py          # Chains the 3 agents, times the run, enforces the SLA
│   ├── config.py                # Environment + provider settings
│   ├── verify.py                # Dependency-free checker (local or against a live URL)
│   ├── debug_case.py            # Shows extracted features + every matching rule
│   ├── agents/
│   │   ├── symptom_analyzer.py  # Agent 1 — LLM + deterministic extractor
│   │   ├── triage_router.py     # Agent 2 — rule engine, never an LLM
│   │   └── care_pathway.py      # Agent 3 — SHA costs, instructions, danger signs
│   ├── triage/
│   │   ├── extractor.py         # Bilingual keyword/regex feature extraction
│   │   └── engine.py            # Predicate rule engine
│   ├── llm/client.py            # Provider-agnostic LLM wrapper (never raises)
│   ├── knowledge/loader.py      # Reads data/*.json and validates it at boot
│   ├── data/                    # The knowledge base (JSON, no database)
│   │   ├── conditions.json      # 10 Kenyan conditions
│   │   ├── triage_rules.json    # 26 ordered RED/YELLOW/GREEN rules
│   │   ├── sha_benefits.json    # PHF / SHIF / ECCIF coverage
│   │   ├── swahili_translations.json
│   │   └── test_cases.json      # 5 demo scenarios + 5 regression cases
│   ├── tests/                   # pytest suite, no network required
│   └── requirements.txt
├── frontend/                    # Next.js app (pages router)
│   ├── src/
│   │   ├── pages/               # index, intake, results, demo
│   │   ├── components/          # IntakeForm, TriageResult, ReferralSlip
│   │   ├── utils/               # api-client.js, formatOutput.js
│   │   └── styles/              # colors.css tokens + mobile-first.css
│   └── scripts/
│       └── verify-api-contract.mjs   # Fails if the UI would render an object
├── docs/
│   ├── API_DOCS.md              # Endpoint reference
│   ├── DEPLOYMENT.md            # Render + Vercel, step by step
│   ├── ARCHITECTURE_NOTES.md    # Design decisions + deviations from the plan
│   └── plan/                    # The original planning documents
├── AGENT.md                     # Frontend ↔ backend integration contract
├── render.yaml                  # Render blueprint (native Python, no Docker)
└── README.md
```

---

## ⚙️ Running locally

**Backend** (port 8000)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Check <http://localhost:8000/health>, and <http://localhost:8000/docs> for interactive API docs.
No API key is required — without one the service runs deterministically and all three triage
levels still work. Add a free Gemini key (<https://aistudio.google.com/apikey>) to enable AI
structuring and phrasing.

**Frontend** (port 3000)

```bash
cd frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## ✅ Testing

```bash
# backend: unit + scenario + regression + API tests (no network, no API key)
cd backend && python -m pytest tests/ -q

# backend: dependency-free end-to-end check of all 5 scenarios
python verify.py
python verify.py --url https://YOUR-SERVICE.onrender.com

# frontend ↔ backend contract (backend must be running)
cd frontend && node scripts/verify-api-contract.mjs
```

`verify-api-contract.mjs` exists because `next build` cannot catch a UI bug that only appears with
real data: two backend fields are objects (`facility`, `cost`), and rendering one directly throws
*"Objects are not valid as a React child"* and blanks the page. The script pushes all 5 scenarios
through the frontend's own adapter and fails if any field would render as an object.

`debug_case.py` is the triage diagnostic:

```bash
cd backend && python debug_case.py "severe chest pain and I cannot breathe" 52
```

---

## 🔌 API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + configuration (Render polls this) |
| `GET` | `/` | Landing payload, so a bare URL is not a 404 |
| `POST` | `/api/analyze-symptoms` | Agent 1 — structures raw symptom text |
| `POST` | `/api/triage-decision` | Agent 2 — returns RED / YELLOW / GREEN |
| `POST` | `/api/care-pathway` | Agent 3 — instructions + SHA cost |
| `POST` | `/api/full-triage` | All three agents chained — what the UI calls |
| `GET` | `/api/demo/test-cases` | The 5 demo scenarios, for one-click demos |
| `GET` | `/api/rules` | The rule set, for clinician review |

Full request/response examples: [`docs/API_DOCS.md`](docs/API_DOCS.md) ·
Integration contract: [`AGENT.md`](AGENT.md)

---

## 🎬 The 5 demo scenarios

| # | Scenario | Age | Expected | SHA fund |
|---|---|---|---|---|
| 1 | Malaria suspicion — fever, chills, headache | 25 | **YELLOW** | PHF |
| 2 | Routine hypertension review, 135/85 | 55 | **GREEN** | PHF |
| 3 | Severe chest pain with breathlessness | 52 | **RED** | ECCIF |
| 4 | Depression with suicidal ideation | 28 | **RED** | SHIF |
| 5 | Child with a common cold, 37.5 °C | 8 | **GREEN** | PHF |

`backend/tests/test_scenarios.py` enforces every one. If a rule or prompt change alters any level,
the suite fails with an explanation.

---

## 🇰🇪 SHA, not NHIF

NHIF was replaced by the **Social Health Authority (SHA)** in October 2024, so every cost statement
names one of SHA's three funds:

- **Primary Healthcare Fund (PHF)** — free routine and preventive care at dispensary / health-centre
  level (GREEN and most YELLOW cases)
- **Social Health Insurance Fund (SHIF)** — inpatient, specialist and urgent care (YELLOW / RED)
- **Emergency, Chronic and Critical Illness Fund (ECCIF)** — emergencies and catastrophic care (RED)

A test asserts the string `NHIF` never appears in any API response. Background:
[`docs/plan/SHA_UPDATE_CRITICAL.md`](docs/plan/SHA_UPDATE_CRITICAL.md)

---

## 🔐 Clinical safety posture

This is a hackathon prototype and the repository does not pretend otherwise.

- `clinical_reviewed: false` on every condition — no clinician has signed off yet.
- `triage_rules.json` carries a `PILOT_TODO` list of what must be validated before real use.
- Every output carries a "guidance only, not a diagnosis" disclaimer.
- The system never names a definitive diagnosis; it reports findings and urgency.
- Rules are ordered so that **no RED rule can be shadowed** by a YELLOW or GREEN rule — asserted by
  a test.
- Nothing is persisted: no patient data is stored. Authentication and an audit log are required
  before any pilot.

---

## 👥 Team

| Role | Focus |
|---|---|
| Lead Developer + DevOps | AI agents, deterministic engine, backend, deployment |
| Frontend Developer | Next.js app, mobile UI, referral slip |
| Data Specialist | Conditions, triage rules, SHA mapping, test cases |
| Clinical/Product Researcher | Kenya context validation, post-hackathon roadmap |

---

## 🗺️ Roadmap after the hackathon

1. **Weeks 1–2:** apply to Kenya's Digital Health Agency regulatory sandbox
2. **Months 1–3:** pilot with 5–10 real dispensaries; clinician review of the rule set
3. **Months 3–6:** refine triage rules with clinician feedback; native-speaker Swahili review
4. **Months 6–12:** scale to a county Primary Care Network (100+ facilities)
5. **Year 2+:** explore integration with the Taifa Care platform

---

## 📄 Licence

Team-owned original work, built for the GOMYCODE *Come Build with AI* hackathon. Third-party
models, datasets and libraries remain under their own licences; see `AGENT.md` for the AI/tool
disclosure used in the submission.
