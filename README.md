# MediTriage AI 🏥

**Smart healthcare triage for Kenya's Primary Care Network** — an AI system that listens to patient symptoms and instantly tells health workers whether a patient needs a hospital (🔴 RED), urgent clinic care (🟡 YELLOW), or routine treatment (🟢 GREEN).

Built at the GOMYCODE Hackathon, September 25–27, 2026.

[![Frontend](https://img.shields.io/badge/frontend-live-brightgreen)](https://medi-triage.vercel.app)
[![Backend](https://img.shields.io/badge/backend-Render-blue)](https://medi-triage-backend.onrender.com/health)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20Claude-purple)](#tech-stack)

---

## 🚀 Try It Now

**Live demo:** [medi-triage.vercel.app](https://medi-triage.vercel.app)
**Backend health check:** [medi-triage-backend.onrender.com/health](https://medi-triage-backend.onrender.com/health)

1. Open the live link above
2. Click **Start Triage**
3. Type a symptom description, e.g. *"I have fever, headache, and body aches for 2 days"*
4. Get a RED / YELLOW / GREEN result with cost info and next steps — in under 30 seconds
5. Print the referral slip

> ⚠️ Replace the badge/demo links above with your final Vercel and Render URLs once deployed — these are placeholders from the project plan.

---

## 🩺 The Problem

Kenya's health clinics see 50–80+ patients a day. Triage is currently done by gut feel:
- Urgent cases (malaria, chest pain) sometimes wait behind routine checkups
- Routine cases get referred to hospitals unnecessarily, wasting patients' time and money
- Telemedicine is growing, but there's no standardized way to triage symptoms called or messaged in

## 💡 The Solution

MediTriage AI triages patients in **under 30 seconds**, from home or at the clinic:

- Works on any phone, even with slow internet (USSD/SMS fallback for 2G areas)
- Understands English and Swahili
- Covers Kenya's top 10 primary-care conditions (malaria, TB, hypertension, UTI, and more)
- Explains costs clearly under Kenya's **SHA (Social Health Authority)** — the three-fund system (PHF / SHIF / ECCIF) that replaced NHIF in October 2024
- Gives a printable referral slip in plain language

---

## 🖥️ How It Works
PATIENT (at home or at clinic)
↓
Describes symptoms (text, English or Swahili)
↓
AI Agent 1: Symptom Analyzer → structures symptoms, severity, red flags
↓
AI Agent 2: Triage Router → decides RED / YELLOW / GREEN
↓
AI Agent 3: Care Pathway → where to go, what to bring, what it costs
↓
Patient / nurse gets a clear, printable result

See [`docs/TECHNICAL_ARCHITECTURE.md`](docs/TECHNICAL_ARCHITECTURE.md) for the full system diagram, agent logic, and API contracts.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js, deployed to Vercel |
| Backend | FastAPI (Python), deployed to Render |
| AI | Claude API (multi-agent orchestration) + NVIDIA Brev |
| Data | SQLite / JSON — 10 conditions, triage rules, SHA benefit mapping |

---

## 📁 Repository Structure
medi-triage-ai/
├── frontend/ # React/Next.js app
│ ├── pages/
│ ├── components/
│ └── public/
│
├── backend/ # FastAPI app
│ ├── main.py # API + agent orchestrator
│ ├── agents/
│ │ ├── symptom_analyzer.py # Agent 1
│ │ ├── triage_router.py # Agent 2
│ │ └── care_pathway.py # Agent 3
│ ├── data/
│ │ ├── conditions.db
│ │ ├── triage_rules.json
│ │ └── test_cases.json
│ └── requirements.txt
│
├── docs/
│ ├── TEAM_BRIEF.md # Non-technical project explainer
│ ├── TECHNICAL_ARCHITECTURE.md
│ ├── API_DOCS.md
│ └── DEPLOYMENT.md
│
├── .env.example
└── README.md

---

## ⚙️ Running Locally

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your CLAUDE_API_KEY
uvicorn main:app --reload
```
Backend runs at `http://localhost:8000` — check `/health`.

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env.local   # set API endpoint to http://localhost:8000
npm run dev
```
Frontend runs at `http://localhost:3000`.

---

## 🔌 API Overview

| Endpoint | Purpose |
|---|---|
| `POST /api/analyze-symptoms` | Agent 1 — structures raw symptom text |
| `POST /api/triage-decision` | Agent 2 — returns RED / YELLOW / GREEN |
| `POST /api/care-pathway` | Agent 3 — returns instructions + cost info |
| `POST /api/full-triage` | Runs all three agents in one call |
| `GET /health` | Service health check |

Full request/response examples: [`docs/API_DOCS.md`](docs/API_DOCS.md)

---

## 🇰🇪 About SHA Coverage

This project uses Kenya's **Social Health Authority (SHA)**, which replaced NHIF in October 2024. Triage results reference the three SHA funds:

- **Primary Healthcare Fund (PHF)** — free routine/preventive care at dispensary level (GREEN cases)
- **Social Health Insurance Fund (SHIF)** — inpatient, specialist, urgent care (YELLOW/RED cases)
- **Emergency, Chronic and Critical Illness Fund (ECCIF)** — emergencies and catastrophic care (RED cases)

More detail: [`docs/SHA_UPDATE_CRITICAL.md`](docs/SHA_UPDATE_CRITICAL.md)

---

## 👥 Team

| Role | Focus |
|---|---|
| Lead Developer + DevOps | AI agents, backend, deployment |
| Frontend Developer | React app, mobile UI, referral slip |
| Data Specialist | Disease database, triage rules, test cases |
| Clinical/Product Researcher | Kenya context validation, post-hackathon roadmap |

---

## 🗺️ Roadmap After the Hackathon

1. **Weeks 1–2:** Apply to Kenya's Digital Health Agency regulatory sandbox
2. **Months 1–3:** Pilot with 5–10 real dispensaries
3. **Months 3–6:** Refine triage rules with clinician feedback
4. **Months 6–12:** Scale to a full county Primary Care Network (100+ facilities)
5. **Year 2+:** Explore integration with the Taifa Care platform

---

## 📄 Licence
