# MediTriage AI - Project Overview

## Project Title
**MediTriage AI: Smart Healthcare Triage for Kenya's Primary Care Network**

---

## What We're Building (In One Sentence)
An AI system that listens to patient symptoms and instantly tells health workers whether a patient needs a hospital (RED), urgent clinic care (YELLOW), or routine treatment (GREEN).

---

## Why This Matters

**The Problem:**
- Kenya's health clinics are overwhelmed with patients
- Nurses make triage decisions by gut feel, not data
- Some urgent patients are missed, some routine patients waste time/money

**Our Solution:**
- AI analyzes symptoms in **30 seconds**
- Color-codes urgency: RED (emergency) → YELLOW (urgent) → GREEN (routine)
- Works on any phone, even in areas with slow internet
- Understands Kenya's diseases (malaria, TB) and costs (SHA (Social Health Authority) coverage)
- Gives clear instructions that patients can understand

**Real Impact:**
- Saves lives by flagging emergencies faster
- Reduces hospital overcrowding by routing routine cases correctly
- Saves patients money by being transparent about costs
- Helps overworked nurses make better decisions

---

## How It Works (Two Scenarios)

```
SCENARIO A: PATIENT AT HOME (TELEMEDICINE)
Patient feels sick at home
       ↓
Opens app on phone, enters symptoms
(or calls clinic, nurse enters symptoms)
       ↓
AI analyzes in 30 seconds
       ↓
AI says: RED (go to hospital NOW)
        YELLOW (come to clinic today)
        GREEN (manage at home, no visit needed)
       ↓
Patient gets instructions + cost info
       ↓
Patient decides: Go to hospital, go to clinic, or stay home

SCENARIO B: PATIENT AT CLINIC (IN-PERSON)
Patient arrives at busy clinic
       ↓
Nurse enters symptoms on tablet
(MediTriage speeds up triage process)
       ↓
AI confirms: RED/YELLOW/GREEN in seconds
       ↓
Nurse sees urgent patients (RED) first
       ↓
Patient treated efficiently, clinic saves time
```

---

## Project Structure

### **4 AI Agents (The Brain)**

1. **Symptom Analyzer** 
   - Reads what patient says
   - Extracts symptoms, severity, red flags
   - Understands Swahili + English

2. **Triage Router**
   - Decides if RED, YELLOW, or GREEN
   - Uses Kenya clinical guidelines
   - Based on disease burden + context

3. **Care Pathway Recommender**
   - Tells patient where to go
   - What to bring, what to expect
   - Shows if it's free or costs money

4. **Outcome Tracker** (Future - not for hackathon)
   - SMS follow-ups
   - Collects feedback
   - Identifies patterns for improvement

### **Frontend (The Face)**
- Mobile-first web app (works on phones)
- Beautiful color-coded results (RED/YELLOW/GREEN)
- Printable referral slip nurses can use
- Simple language, no medical jargon

### **Backend (The Engine)**
- FastAPI Python server
- Connects to Claude API for AI decisions
- Integrates NVIDIA Brev for speed
- Deployed to Render cloud

### **Database (The Knowledge)**
- 10 most common Kenyan health conditions
- Triage rules (what makes something RED/YELLOW/GREEN)
- SHA (Social Health Authority) benefit info (what's free vs. costs money)
- 5 test patient scenarios for demo

---

## Team Structure

| Person | Role | Deliverable |
|--------|------|-------------|
| **Geofry (You)** | Lead Developer + DevOps | Build AI agents, backend logic, deploy to Render + Vercel, GitHub setup |
| **Person 2** | Frontend Developer | Build React app, mobile UI, printable referral slip |
| **Person 3** | Data Specialist | Create disease database, triage rules, test cases |
| **Person 4** | Clinical/Product Researcher | Validate Kenya context, write clinic workflow doc, plan post-hackathon roadmap |

---

## Timeline

| Date | What | Who | Key Deliverable |
|------|------|-----|-----------------|
| **Sept 25** | Kickoff + Setup | All | GitHub repo, dev environments ready |
| **Sept 25-26** | Heavy Dev | Geofry + Person 2 | AI agents + frontend UI working |
| **Sept 26** | Integration | All | Backend + Frontend talking to each other |
| **Sept 26 EOD** | Deployment | Person 4 | Live URLs (Vercel + Render) |
| **Sept 27 Morning** | Final Testing | All | All 5 scenarios work, URLs live |
| **Sept 27, 9 AM** | Demo | All | Judges test the system |

---

## What Success Looks Like

### For Judges
✅ Sees the demo  
✅ Understands it solves a real Kenya problem  
✅ Sees triage decisions are fast + accurate  
✅ Recognizes it could scale to 100+ clinics  

### For Your Team
✅ All code works  
✅ App is live on internet  
✅ Demo runs smoothly  
✅ You can explain what each part does  

### For Kenya's Clinics
✅ Can use this tomorrow to help patients  
✅ Makes triage faster + more consistent  
✅ Reduces unnecessary referrals  
✅ Saves money + lives  

---

## 10 Kenyan Conditions We're Triaging

1. **Malaria** (13-15% of visits) → HIGH PRIORITY
2. **Respiratory Infection** (Cough, cold, bronchitis)
3. **Hypertension** (High blood pressure)
4. **Diarrhea/Gastroenteritis**
5. **Chest Pain** (Could be cardiac)
6. **Depression/Anxiety** (Mental health)
7. **Urinary Tract Infection (UTI)**
8. **Skin Infection**
9. **Diabetes**
10. **Minor Injury/Trauma**

---

## Key Features (Why We're Different)

| Feature | Why It Matters |
|---------|------------------|
| **Kenya-Focused** | Knows Kenya diseases, costs, SHA (Social Health Authority) coverage |
| **Works Offline** | USSD SMS fallback for 2G phones in rural areas |
| **Multilingual** | Swahili + English (speaks what patients speak) |
| **Fast** | Result in <30 seconds (not 10 minutes) |
| **Printable** | Gives health worker a slip to hand patient |
| **Cost-Transparent** | Tells patient upfront: "Free" or "~KES 500" |
| **Real Problem** | Tested with actual Kenya Primary Care Network data |

---

## Demo Script (For Sept 27)

```
JUDGE: "Show me how this works"

YOU: 
1. Open www.medi-triage.vercel.app in browser
2. Click "Start Triage"
3. Type: "I have fever, headache, and body aches for 2 days"
4. Hit submit
5. [AI processes] — shows YELLOW (Urgent, go to clinic today)
6. "This is malaria suspicion, common in Kenya. Free under SHA (Social Health Authority)."
7. Print button → referral slip
8. [Repeat with 4 more scenarios]

JUDGE: "So this really works for Kenya?"

YOU:
"Yes. Malaria is 13-15% of clinic visits. Nurses see 60+ patients/day in small dispensaries. 
This helps them triage fast, accurately. It's built for Kenya's reality — low internet, 
non-specialist staff, high disease burden. After we win this hackathon, we're applying 
for a regulatory sandbox with Kenya's Digital Health Agency."
```

---

## One-Page Cheat Sheet

**Project Name:** MediTriage AI

**Problem:** Kenya's clinics are overwhelmed; triage is inconsistent

**Solution:** AI reads symptoms → says RED/YELLOW/GREEN in 30 seconds

**Proof:** Works for Kenya's top 10 diseases (malaria, TB, hypertension, etc.)

**Team:** 4 people, 3 days

**Tech Stack:**
- Frontend: React/Next.js (Vercel)
- Backend: FastAPI (Render)
- AI: Claude API + NVIDIA Brev
- Data: JSON (conditions, rules, test cases)

**Live URLs (Sept 27):**
- Frontend: https://medi-triage.vercel.app
- Backend: https://medi-triage-backend.onrender.com/health
- GitHub: github.com/geoduor/medi-triage-ai

**Success Metric:** Judges see 5 scenarios triaged correctly in 2 minutes

---

## Files You'll Use

| File | What | Owner |
|------|------|-------|
| `TEAM_BRIEF.md` | Non-technical explanation | Read this first! |
| `TECHNICAL_ARCHITECTURE.md` | How to build each part | Geofry + Person 2 |
| `TEAM_TASK_BREAKDOWN.md` | Step-by-step tasks | Your personal roadmap |
| `PROJECT_OVERVIEW.md` | This file | Quick reference |

---

## Questions to Ask Before You Start

**"What if the API is slow?"**  
→ NVIDIA Brev will optimize. Also: timeout handling + cached responses.

**"What if someone enters symptoms in Kikuyu (not English/Swahili)?"**  
→ Claude handles many languages. But for MVP, we focus on English + Swahili (most common in Kenya health clinics).

**"What if we disagree on triage decision?"**  
→ We document our rules. Judges understand it's MVP. After hackathon: validate with real health workers.

**"What if network is down during demo?"**  
→ We have cached test results. Also: USSD fallback explained (we show pseudocode).

**"What if Render goes down?"**  
→ Have backup: deploy to Railway or AWS Lambda. But Render is solid for hackathon.

---

## After the Hackathon (Roadmap)

**Week 1-2:** Regulatory sandbox application (Kenya Digital Health Agency)

**Month 1-3:** Pilot with 5-10 real dispensaries (partner with Ministry of Health)

**Month 3-6:** Feedback loops, improve decision rules with clinician input

**Month 6-12:** Scale to one county's PCN network (100+ facilities)

**Year 2+:** National integration with Taifa Care platform

---

## Let's Build

This is a real problem solving a real need in Kenya. Your code will help people.

**Sept 25-27:** Build it.  
**Sept 27:** Demo it.  
**Sept 28+:** Deploy it.  

See you at the kickoff.

---

**For questions, reference docs:**
- Architecture questions → `TECHNICAL_ARCHITECTURE.md`
- Task questions → `TEAM_TASK_BREAKDOWN.md`
- What we're building → `TEAM_BRIEF.md`
- Big picture → This file

**Lead:** Geofry Oduor  
**Hackathon:** GOMYCODE, Sept 27, 2026  
**Goal:** WIN + Help Kenya's Clinics
