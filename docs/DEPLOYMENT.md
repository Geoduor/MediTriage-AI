# MediTriage AI - Deployment

**Owner:** Person 1 (Lead Developer + DevOps)

This is the document the architecture plan required: live URLs, deploy steps, and
the environment variables each service needs.

---

## Live URLs

Fill these in as you deploy. They are the deliverable.

| Service | Platform | URL | Status |
|---|---|---|---|
| Backend API | Render | `https://medi-triage-backend.onrender.com` | NOT DEPLOYED |
| Backend health | Render | `https://medi-triage-backend.onrender.com/health` | NOT DEPLOYED |
| Backend docs | Render | `https://medi-triage-backend.onrender.com/docs` | NOT DEPLOYED |
| Frontend | Vercel | `https://medi-triage.vercel.app` | NOT DEPLOYED |
| Repository | GitHub | `https://github.com/geoduor/medi-triage-ai` | NOT PUSHED |

Verify any deployment with:

```bash
cd backend
python verify.py --url https://medi-triage-backend.onrender.com
```

That runs the full scenario suite against the live service and exits non-zero if
anything is wrong. Run it before you demo, not after.

---

## Prerequisites

```bash
git --version
python --version     # 3.11+ (3.14 works locally)
node --version       # 18+ for the frontend
```

Accounts needed: GitHub, Render, Vercel. An Anthropic API key is **optional** -
the backend triages correctly without one.

---

## Step 1 - Push to GitHub

From the repository root:

```bash
cd C:\Users\user\Desktop\PROJECTS\MediTriage-AI
git init
git add .
git commit -m "MediTriage AI: backend, knowledge base, tests, frontend scaffold"

# Create the empty repo on GitHub first, then:
git remote add origin https://github.com/geoduor/medi-triage-ai.git
git branch -M main
git push -u origin main
```

Confirm before pushing that secrets are **not** staged:

```bash
git status --short
```

`.gitignore` excludes `.env`, `.libs/`, `.tmp/`, `node_modules/` and `.next/`.
If `git status` ever shows `.env`, stop and fix it before pushing.

---

## Step 2 - Deploy the backend to Render (no Docker)

### Option A: Manual web service (what you'll actually click)

You already have a Render account, so this is the direct path:

1. Render dashboard -> **New +** -> **Web Service**
2. Connect your GitHub account (once) and pick `medi-triage-ai`
3. Configure the service:

| Field | Value |
|---|---|
| Name | `medi-triage-backend` (your URL becomes `medi-triage-backend.onrender.com`) |
| Region | **Frankfurt** (closest to Kenya of the free options) |
| Root directory | `backend` |
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Free |

4. **Advanced -> Environment Variables** - add the variables from the table below
   (minimum: `PYTHON_VERSION`, `CORS_ORIGINS`; `GEMINI_API_KEY` optional)
5. **Advanced -> Health Check Path**: `/health` (should default to this from `render.yaml`)
6. **Create Web Service** - first deploy takes ~2-3 minutes

No Docker, no container: Render installs the pinned `requirements.txt` into its
native Python 3 environment and runs uvicorn directly.

### Option B: Blueprint (one file, zero clicking)

`render.yaml` in the repository root already describes the same service.

1. Render dashboard -> **New +** -> **Blueprint**
2. Select the repository
3. Render reads `render.yaml`, creates `medi-triage-backend`, and prompts for
   `GEMINI_API_KEY` (leave blank to run deterministic)
4. Deploy

### Environment variables

| Key | Value | Required |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | recommended |
| `ENVIRONMENT` | `production` | no |
| `LOG_LEVEL` | `INFO` | no |
| `LLM_MODE` | `auto` | no |
| `LLM_PROVIDER` | `gemini` (recommended) | no |
| `LLM_MODEL` | `gemini-2.5-flash-preview` | only if using the LLM |
| `LLM_TIMEOUT_SECONDS` | `20` | no |
| `CORS_ORIGINS` | `http://localhost:3000,https://medi-triage.vercel.app` | **yes** |
| `GEMINI_API_KEY` | free key from https://aistudio.google.com/apikey | no |

The LLM is optional. With `GEMINI_API_KEY` blank the service runs
deterministically and still triages correctly. Other providers (`groq`,
`ollama`, `anthropic`) are supported through `LLM_PROVIDER` - see
`.env.example` for their keys. Ollama cannot power a Render deployment because
it runs locally on your machine.

**`CORS_ORIGINS` is the one that bites.** If the Vercel URL is not listed, every
browser request from the frontend is blocked and the demo shows a network error.
Update it after the frontend deploys.

### Render free tier warning

Free Render services sleep after ~15 minutes of inactivity and take 30-60 seconds
to wake. **Open the health URL a few minutes before you demo** so the first judge
request is not a 50-second cold start.

### Verify

```bash
curl https://YOUR-SERVICE.onrender.com/health
cd backend && python verify.py --url https://YOUR-SERVICE.onrender.com
```

---

## Step 3 - Deploy the frontend to Vercel

The `frontend/` directory is a Person 1 scaffold so this step is not blocked on
Person 2. Person 2 owns the real UI.

1. Vercel dashboard -> **Add New** -> **Project** -> import the repository
2. **Root Directory: `frontend`** (easy to miss - the repo root is not a Next.js app)
3. Framework preset: Next.js (auto-detected)
4. Environment variable:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://medi-triage-backend.onrender.com` |

5. Deploy

`NEXT_PUBLIC_*` variables are baked in at build time. If you change the backend
URL you must **redeploy**, not just edit the variable.

### Verify

Open the Vercel URL. The status line under the heading should read
`Backend: ... - online`. Then click a demo scenario chip and confirm the result
renders.

---

## Step 4 - Wire the two together

1. Copy the Vercel URL
2. Render -> `medi-triage-backend` -> Environment -> set
   `CORS_ORIGINS=http://localhost:3000,https://YOUR-APP.vercel.app`
3. Save; Render redeploys automatically
4. Reload the frontend and run all 5 scenarios

If the frontend cannot reach the backend, check in this order:
CORS setting, `NEXT_PUBLIC_API_URL`, backend cold start, backend `/health`.

---

## No Docker needed

Render runs the backend natively - no container, no Dockerfile. The service
builds with `pip install -r requirements.txt` and starts with
`uvicorn main:app --host 0.0.0.0 --port $PORT`, exactly as configured in
`render.yaml` and in Step 2 above. Nothing in this project requires Docker.

---

## NVIDIA Brev

The architecture plan lists NVIDIA Brev for embeddings and inference acceleration.
**It is not on the critical path and the system does not use it.**

Being accurate about this matters more than claiming it: Brev is GPU
infrastructure, and this workload is a rules engine plus two short LLM calls
with no embeddings. Adding Brev would increase latency and deployment risk for no
functional gain. The plan's `/api/rules` and `/api/analyze-symptoms` endpoints
make the engine inspectable without it.

If you want to mention it to judges, describe it as the scaling path for
symptom-similarity embeddings across a large case corpus once real clinic data
exists - which is honest, and is what the plan intended it for.

Three cheaper wins are already in place:

| Instead of | We have | Effect |
|---|---|---|
| GPU inference | Deterministic rule engine | 5-17 ms, no GPU |
| Embedding similarity | Keyword taxonomy + rule predicates | Explainable, offline |
| LLM on the critical path | LLM as optional enhancement (Gemini by default) | Demo cannot fail on API issues |

---

## Pre-demo checklist

Run through this an hour before presenting.

- [ ] `cd backend && python -m pytest tests/ -q` -> all pass
- [ ] `python verify.py` -> ALL CHECKS PASSED
- [ ] `python verify.py --url <render-url>` -> ALL CHECKS PASSED
- [ ] Backend `/health` returns `"status": "ok"`
- [ ] Backend warmed up (hit `/health` once to defeat the cold start)
- [ ] `CORS_ORIGINS` contains the exact Vercel URL
- [ ] Frontend loads and the status line says **online**
- [ ] All 5 demo scenarios return the expected level through the UI
- [ ] Swahili scenario renders Swahili text
- [ ] Print preview shows a clean one-page referral slip
- [ ] Decide `LLM_MODE`: `off` is the safest demo setting
- [ ] Laptop charging, mobile hotspot ready
- [ ] `backend/data/test_cases.json` open, in case you need to type symptoms manually

### If something breaks mid-demo

| Symptom | Cause | Fix |
|---|---|---|
| Frontend: cannot reach service | CORS or wrong API URL | Check `CORS_ORIGINS`; set `LLM_MODE=off` and redeploy |
| First request takes ~50s | Render free tier cold start | Wait; it is a one-time cost |
| LLM errors in logs | Bad key or quota | Harmless: the engine still triages. `LLM_MODE=off` silences it |
| Wrong triage level | Rule or keyword issue | `python debug_case.py "<the symptoms>"` to see the exact rule |
| Backend 500 | Knowledge base file malformed | `python -c "import json;json.load(open('data/triage_rules.json'))"` |

`debug_case.py` is the tool for triage problems. It prints the extracted
features, every matching rule in priority order, and the rule that won.
