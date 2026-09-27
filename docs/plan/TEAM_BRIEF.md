# MediTriage AI - Team Briefing Document

## Project Title
**MediTriage AI: Kenya's Smart Healthcare Triage System**

---

## What Are We Building? (In Plain English)

Imagine you work at a busy health clinic in Kisumu or Nairobi. You're seeing 60+ patients a day, and they all arrive with different problems — fever, cough, hypertension follow-up, depression, UTI. You have only 2 hours to see everyone. Without triage, a serious malaria case waits behind a routine blood pressure check.

**MediTriage AI solves this problem.**

We're building an AI system that acts like an intelligent health assistant. Patients (or health workers) can **use it from home on their phone** or **at the clinic on a tablet**. When they describe symptoms, our system immediately figures out:

1. **How urgent is this?** (Emergency? Can wait a few hours? Routine?)
2. **Where should they go?** (Hospital? Clinic? Home with advice?)
3. **What will it cost?** (Free under insurance? Will they afford it?)
4. **What should they do NOW?** (Simple instructions they can understand)

This keeps clinics organized, saves lives, and prevents unnecessary trips to expensive hospitals.

---

## Why Does Kenya Need This?

**The Problem:**
- Health clinics in towns, suburbs, and urban areas are overwhelmed with patients (especially after government expanded healthcare access through Primary Care Networks)
- Nurses make triage decisions by gut feel, not data → some urgent cases are missed, some routine patients unnecessarily referred to hospitals
- Patients don't know if they need a hospital or just home rest → waste time, money on transport/unnecessary referrals
- Telemedicine expanding, but no standardized triage when patients call/message with symptoms

**Our Solution:**
- An AI that triages patients in **30 seconds**
- Works on **any phone** (even old ones without good internet)
- Understands **Swahili and English**
- Tells patients the truth about costs (free vs. ~KES 500)
- Helps nurses make better, faster decisions

---

## What Makes This Different?

Other triage apps (like Infermedica, Ada Health) were built for rich countries with:
- Hospitals full of doctors
- Fast internet everywhere
- Patients who can afford expensive care

**Our system is built for Kenya:**
- Works in areas with slow internet (USSD fallback for 2G phones)
- Handles tropical diseases (malaria, TB) that don't exist in rich countries
- Knows about Kenya's health insurance - SHA (Social Health Authority) (Social Health Authority)) and what's free
- Written in Swahili so patients understand

---

## How It Works (The Simple Version)

```
SCENARIO A: Patient at home (Telemedicine)
Patient feels sick, opens app/calls clinic
         ↓
Types symptoms into phone (or health worker takes notes)
         ↓
AI listens, understands, asks follow-up questions
         ↓
AI says: "RED (go to hospital NOW)" or "YELLOW (come to clinic today)" or "GREEN (manage at home)"
         ↓
Patient gets printable/SMS instructions + cost info
         ↓
Patient decides: Go to hospital, go to clinic, or stay home

SCENARIO B: Patient at clinic (In-person)
Patient arrives at health clinic
         ↓
Nurse types/enters symptoms into tablet/phone
         ↓
AI analyzes quickly
         ↓
AI confirms: "YELLOW - see this patient now" (instead of waiting 2 hours)
         ↓
Nurse can see urgent patients first, use time efficiently
```

---

## Our Hackathon Demo (Sept 27)

We have **one day** to build and demo this. Here's what we'll show judges:

**5 Test Patients:**
1. Someone with malaria (RED - needs hospital fast)
2. Someone with high blood pressure follow-up (GREEN - routine)
3. Someone with chest pain (RED - emergency!)
4. Someone with depression symptoms (YELLOW - needs counselor)
5. Someone with a cough/cold (GREEN - home care)

**The demo workflow:**
- Judges ask questions about each patient
- We type/speak symptoms into our app
- AI instantly triages (RED/YELLOW/GREEN)
- We print out a referral slip
- Judges see it's fast, accurate, and useful for Kenya

---

## Team Roles (Who Does What)

### **Geofry (You - Lead Developer + DevOps)**
- **Backend:** Build FastAPI server + 4 AI agents (Claude API) + orchestrator
- **DevOps:** GitHub repo setup, Render backend deployment, Vercel frontend deployment, NVIDIA Brev setup
- **Coordinate:** Make sure everyone's code works together
- **Deliverable:** Working backend API + both apps live on internet (Vercel + Render URLs)

### **Person 2 (Frontend Developer)**
- **What:** Build the app that patients/nurses use
- **How:** React/Next.js, mobile-first design, colorful (RED/YELLOW/GREEN buttons)
- **Deliverable:** Beautiful, easy-to-use phone/web app

### **Person 3 (Data/Content Specialist)**
- **What:** Create the disease database and test patients
- **How:** List 10 common Kenyan diseases, symptoms for each, SHA (Social Health Authority) costs
- **Deliverable:** Test cases that Person 2 and Geofry use to demo the system

### **Person 4 (Clinical/Product Research)**
- **What:** Research + validate Kenya healthcare context, create user testing plan
- **How:** Document real clinic workflows, validate our assumptions, test with health workers
- **Deliverable:** 
  - Clinic workflow document (how real triage happens now)
  - Validation document (does our triage match real clinic needs?)
  - User testing script (what to ask health workers about the prototype)
  - Post-hackathon research roadmap (regulatory requirements, clinic partnerships)

---

## What Success Looks Like

✅ **Judge asks:** "What if someone has fever and headache and chest pain?"  
✅ **You enter symptoms into the app**  
✅ **AI takes 20 seconds, says: RED - go to hospital immediately**  
✅ **App prints referral slip with cost info**  
✅ **Judge says:** "This is EXACTLY what Kenya's clinics need!"

---

## Success Criteria (What We're Measured On)

1. **Works:** Correctly triages 4-5 test patients (RED/YELLOW/GREEN match reality)
2. **Fast:** Results in <30 seconds
3. **Clear:** Output is printable, understandable to a health worker
4. **Real Problem:** Judges recognize it solves a genuine Kenyan healthcare bottleneck
5. **Research-Backed:** We can cite real clinic workflows, demonstrate understanding of Kenya's system
6. **Scalable:** We explain how to partner with Ministry of Health for pilot + scale to 100+ facilities

---

## Key Dates

- **Sept 25 (Tomorrow morning):** Team kickoff, assign roles, set up tools
- **Sept 26 (Friday):** Heavy dev day, integrate all pieces
- **Sept 27 (Saturday morning):** Final polish, test, demo at 9 AM

---

## Questions to Ask Me

- "What's the difference between RED/YELLOW/GREEN?" → Urgency of care needed
- "Will this replace nurses?" → NO. It helps them work faster
- "Does it work offline?" → Yes, we have an USSD (SMS) fallback
- "Why Kenya first?" → Because if it works in Kenya's hardest case, it scales worldwide

---

**Let's build something that saves lives. See you tomorrow.**
