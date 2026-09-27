# MediTriage AI — Frontend

Mobile-first Next.js app for MediTriage AI. See `/AGENT.md` at the repo root for
the full context (API contract, folder structure, design rules, SHA terminology note).

## Setup

```bash
npm install
cp .env.local.example .env.local   # then edit NEXT_PUBLIC_API_URL if needed
npm run dev
```

Visit `http://localhost:3000`.

## Pages

- `/` — home, explains the flow
- `/intake` — symptom intake form → calls `POST /api/full-triage` on submit
- `/results` — color-coded triage result + printable referral slip (reads the result from `sessionStorage`)
- `/demo` — hardcoded scenarios for offline demo / backup if the live API is down

## Deploy

Deployed to Vercel. Set `NEXT_PUBLIC_API_URL` as an environment variable in the
Vercel project settings once the backend is live on Render.
