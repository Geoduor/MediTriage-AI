# MediTriage AI - Technical Architecture

---

## High-Level System Architecture

```
                    ┌─ USERS CAN ACCESS FROM ─┐
                    │                         │
                    ↓                         ↓
            ┌─────────────────┐      ┌────────────────┐
            │   AT HOME       │      │   AT CLINIC    │
            │  (Telemedicine) │      │  (In-Person)   │
            │  Phone/Browser  │      │  Tablet/PC     │
            └────────┬────────┘      └────────┬───────┘
                     │                        │
                     └────────────┬───────────┘
                                  │
                                  ↓
        ┌─────────────────────────────────────────────────┐
        │            FRONTEND (React/Next.js)             │
        │          Mobile-First Web Application           │
        │  ┌──────────────┐  ┌──────────────┐             │
        │  │ Intake Form  │→ │ Triage View  │             │
        │  │ (Symptoms)   │  │ (RED/YELLOW/ │             │
        │  │              │  │  GREEN)      │             │
        │  └──────────────┘  └──────────────┘             │
        │         ↓                    ↑                  │
        │         └────────────────────┘                  │
        │         HTTP API Calls                          │
        │  (Works at clinic OR from home)                 │
        └────────────────┬─────────────────────────────────┘
                         │
                         ↓
        ┌─────────────────────────────────────────────────┐
        │      BACKEND API (FastAPI/Python)               │
        │       (Geofry handles all of this)              │
        │                                                  │
        │  ┌───────────────────────────────────────────┐  │
        │  │      AGENT ORCHESTRATOR                   │  │
        │  │  Coordinates 4 agents + manages flow      │  │
        │  └───────────────┬───────────────┬───────────┘  │
        │                  │               │              │
        │        ┌─────────┴────────┬──────┴────┐          │
        │        ↓                  ↓           ↓          │
        │   ┌─────────┐      ┌──────────┐  ┌──────────┐   │
        │   │Agent 1: │      │ Agent 2: │  │ Agent 3: │   │
        │   │Symptom  │      │ Triage   │  │ Care     │   │
        │   │Analyzer │      │ Router   │  │ Pathway  │   │
        │   │(Claude) │      │(Rules)   │  │(Claude)  │   │
        │   └─────────┘      └──────────┘  └──────────┘   │
        │        ↓                  ↓           ↓          │
        │        └─────────┬────────┴───────┬──────┘       │
        │                  ↓                ↓              │
        │   ┌────────────────────────────────────┐         │
        │   │  KNOWLEDGE BASE / DATABASE        │         │
        │   │  - 10 Conditions                  │         │
        │   │  - Triage Rules (RED/YELLOW/GREEN)│         │
        │   │  - SHA (Social Health Authority) Benefits                  │         │
        │   │  - Care Pathways                  │         │
        │   └────────────────────────────────────┘         │
        └────────────────┬──────────────────────────────────┘
                         │
                  ┌──────┴────────┐
                  ↓               ↓
          ┌──────────────┐  ┌────────────────┐
          │NVIDIA Brev   │  │ Claude API     │
          │(Embeddings+  │  │ (LLM + multi-  │
          │ Speed)       │  │  agent logic)  │
          └──────────────┘  └────────────────┘
```

---

## Agent Breakdown (4 Cores)

### **Agent 1: Symptom Analyzer**
**Purpose:** Understand what the patient is describing

**Input:** 
- Free-text symptoms from patient/nurse
- Patient context (age, HIV status, pregnant, existing conditions)
- Language (English or Swahili)

**Process:**
```python
# Pseudocode
def analyze_symptoms(symptom_text, patient_age, patient_context):
    # Call Claude API
    response = claude.messages.create(
        model="claude-opus-5.5",
        messages=[{
            "role": "user",
            "content": f"""
                Patient: {patient_age} years old, {patient_context}
                Symptoms: {symptom_text}
                
                Extract and structure:
                1. Primary symptom (e.g., fever, chest pain)
                2. Associated symptoms (headache, cough, etc.)
                3. Duration (days)
                4. Severity (mild/moderate/severe)
                5. Red flags (any danger signs?)
                6. Differential considerations
                
                Output as JSON.
            """
        }]
    )
    return json.loads(response.content[0].text)
```

**Output:** Structured JSON with:
- `primary_symptom`: string
- `associated_symptoms`: list
- `duration_days`: int
- `severity`: "mild" | "moderate" | "severe"
- `red_flags`: list
- `differential_considerations`: list

---

### **Agent 2: Triage Router (Rule-Based)**
**Purpose:** Decide urgency level (RED/YELLOW/GREEN)

**Input:** Structured symptom profile from Agent 1

**Logic:**
```python
def triage_decision(symptom_profile, patient_context):
    """
    RED (Emergency) if:
    - Chest pain + shortness of breath
    - Severe difficulty breathing
    - Unconsciousness/altered mental state
    - Signs of severe malaria (high fever + seizures)
    - Vaginal bleeding + pregnancy
    - Any life-threatening emergency sign
    
    YELLOW (Urgent) if:
    - High fever (38.5°C+) with focal symptoms (cough, dysuria)
    - Persistent vomiting/diarrhea with dehydration signs
    - Severe headache + stiff neck (meningitis suspicion)
    - Chest pain without red flags
    - New-onset severe hypertension
    - Mental health crisis (suicidal ideation, severe depression)
    
    GREEN (Routine) if:
    - Common cold/URI symptoms
    - Mild diarrhea
    - Hypertension/diabetes routine monitoring
    - Skin infections (non-spreading)
    - Minor injuries
    """
    
    # Apply rules in order
    if has_emergency_signs(symptom_profile):
        return {"triage_level": "RED", "urgency": "EMERGENCY"}
    elif has_urgent_signs(symptom_profile):
        return {"triage_level": "YELLOW", "urgency": "URGENT"}
    else:
        return {"triage_level": "GREEN", "urgency": "ROUTINE"}
```

**Output:** JSON with:
- `triage_level`: "RED" | "YELLOW" | "GREEN"
- `rationale`: string (why this level)
- `recommended_pathway`: string (hospital | clinic | home)

---

### **Agent 3: Care Pathway Recommender**
**Purpose:** Tell patient/nurse what to do next

**Input:** 
- Triage level from Agent 2
- Symptom profile from Agent 1
- Patient context

**Process:**
```python
def generate_care_pathway(triage_level, symptom_profile, patient_context):
    # For RED cases
    if triage_level == "RED":
        return {
            "instruction": "GO TO HOSPITAL IMMEDIATELY",
            "facility": "Nearest Sub-County Hospital",
            "transport": "Ambulance or fastest available",
            "estimated_cost": "KES 1500-3000 (check with SHA (Social Health Authority))",
            "what_to_bring": ["SHA (Social Health Authority) card", "ID card", "Recent medications"],
            "danger_signs_to_watch": ["Increased confusion", "Worsening pain"]
        }
    
    # For YELLOW cases
    elif triage_level == "YELLOW":
        return {
            "instruction": "Come to clinic TODAY, same day if possible",
            "facility": "This health center",
            "wait_time": "Expected wait: 30-60 mins",
            "cost": "FREE under SHA (Social Health Authority) capitation",
            "what_nurse_will_do": ["Blood tests", "Physical exam", "Treatment decision"],
            "home_care_while_waiting": ["Rest", "Drink plenty water", "Take paracetamol if fever"]
        }
    
    # For GREEN cases
    else:
        return {
            "instruction": "You can manage this at home",
            "self_care": ["Rest", "Hydration", "Nutrition"],
            "when_to_come_in": ["Symptoms worse after 3 days", "New symptoms appear"],
            "medications": ["Over-the-counter options if needed"],
            "estimated_cost": "FREE (no clinic visit needed)",
            "follow_up": "If not better in 5-7 days, visit clinic"
        }
```

**Call Claude for Personalization:**
```python
# Claude personalizes the template
response = claude.messages.create(
    model="claude-opus-5.5",
    messages=[{
        "role": "user",
        "content": f"""
            Patient case: {symptom_profile}
            Triage: {triage_level}
            
            Write SIMPLE, CLEAR instructions for this patient in Swahili.
            - Use short sentences (6-8 words max)
            - Avoid medical jargon
            - Be empathetic
            - Include specific actions
            
            Output as a printable referral slip.
        """
    }]
)
```

**Output:** Printable care plan with:
- `primary_instruction`: string
- `location_to_go`: string
- `expected_cost`: string
- `what_to_bring`: list
- `danger_signs`: list (in Swahili)
- `follow_up_advice`: string

---

### **Agent 4: Outcome Tracker (Future - Skip for MVP)**
This is for POST-hackathon. For demo, just mention it in roadmap.

---

## Frontend Structure (React/Next.js)

```
src/
├── components/
│   ├── IntakeForm.jsx          # Patient symptom input
│   │   ├── SymptomChecklist    # Pre-defined symptoms
│   │   ├── FreeTextInput       # Open-ended text area
│   │   └── PatientContext      # Age, HIV, pregnancy, etc.
│   │
│   ├── TriageResult.jsx        # Color-coded result display
│   │   ├── RedAlert            # Emergency styling
│   │   ├── YellowWarning       # Urgent styling
│   │   └── GreenOK             # Routine styling
│   │
│   └── ReferralSlip.jsx        # Printable output
│       ├── Header              # Clinic name + date
│       ├── PatientInfo         # Name, age, symptoms
│       ├── TriageDecision      # RED/YELLOW/GREEN + rationale
│       └── CareInstructions    # What to do next
│
├── pages/
│   ├── index.jsx               # Home/start page
│   ├── intake.jsx              # Patient intake form
│   ├── results.jsx             # Triage result display
│   └── demo.jsx                # Demo mode (hardcoded test cases)
│
├── api/
│   └── triage/
│       └── route.js            # API endpoint that calls backend
│
├── styles/
│   ├── colors.css              # RED/YELLOW/GREEN theme
│   └── mobile-first.css        # Responsive design
│
└── utils/
    ├── formatOutput.js         # Make results printable
    └── api-client.js           # Call backend

```

---

## Backend API Endpoints (FastAPI/Python)

### Endpoint 1: Analyze Symptoms
```
POST /api/analyze-symptoms
Content-Type: application/json

Request:
{
  "symptoms": "I have fever, headache, and body aches",
  "patient_age": 35,
  "patient_context": {
    "hiv_status": "negative",
    "pregnant": false,
    "chronic_conditions": []
  },
  "language": "en" or "sw"
}

Response:
{
  "primary_symptom": "fever",
  "associated_symptoms": ["headache", "body aches"],
  "duration_days": 2,
  "severity": "moderate",
  "red_flags": [],
  "differential_considerations": ["malaria", "typhoid", "influenza"],
  "agent_1_complete": true
}
```

### Endpoint 2: Get Triage Decision
```
POST /api/triage-decision
Content-Type: application/json

Request:
{
  "symptom_profile": { ...from Agent 1 }
}

Response:
{
  "triage_level": "YELLOW",
  "urgency": "URGENT",
  "rationale": "Fever + headache suggests malaria risk in Kenya",
  "recommended_pathway": "clinic",
  "agent_2_complete": true
}
```

### Endpoint 3: Get Care Pathway
```
POST /api/care-pathway
Content-Type: application/json

Request:
{
  "triage_level": "YELLOW",
  "symptom_profile": { ...from Agent 1 },
  "language": "sw"
}

Response:
{
  "instruction": "Kuja kliniki leo (Come to clinic today)",
  "location": "This health center",
  "cost": "FREE under SHA (Social Health Authority)",
  "self_care": ["Kulia", "Kunywa maji", "Kupumzika"],
  "danger_signs": ["Kufa kwa nia", "Maumau makubwa"],
  "printable_format": true
}
```

---

## Data Schema (SQLite for MVP)

```sql
-- Conditions Database
CREATE TABLE conditions (
  id INTEGER PRIMARY KEY,
  name TEXT,
  kenyan_name_swahili TEXT,
  prevalence_rank INTEGER,  -- 1-10
  typical_age_group TEXT,
  primary_symptoms TEXT,
  red_flag_indicators TEXT,
  treatment_location TEXT,   -- "home" | "clinic" | "hospital"
  estimated_cost TEXT,
  nhif_covered BOOLEAN
);

-- Sample: Malaria
INSERT INTO conditions VALUES (
  1, 
  'Malaria', 
  'Malaria',
  1,
  'All ages',
  'Fever,chills,headache,body aches',
  'High fever+confusion,Seizures,Severe vomiting',
  'clinic',
  '0-500',
  true
);

-- Triage Rules
CREATE TABLE triage_rules (
  id INTEGER PRIMARY KEY,
  symptom_combination TEXT,
  triage_level TEXT,  -- "RED" | "YELLOW" | "GREEN"
  rationale TEXT
);

-- Sample: RED rule
INSERT INTO triage_rules VALUES (
  1,
  'chest_pain + shortness_of_breath',
  'RED',
  'Possible cardiac event - emergency'
);

-- SHA (Social Health Authority) Benefits
CREATE TABLE nhif_benefits (
  id INTEGER PRIMARY KEY,
  facility_level TEXT,  -- "dispensary" | "health_center" | "hospital"
  service_type TEXT,
  cost_to_patient TEXT,
  nhif_covers BOOLEAN
);

-- Sample
INSERT INTO nhif_benefits VALUES (
  1,
  'dispensary',
  'Basic consultation',
  '0',
  true
);
```

---

## Data: 10 Kenyan Conditions for MVP

1. **Malaria** → RED/YELLOW risk, fever 38-40°C, prevalence 13-15% of visits
2. **Respiratory Infection (Cough)** → YELLOW, differential TB/pneumonia
3. **Diarrhea/Gastroenteritis** → GREEN/YELLOW, rehydration key
4. **Hypertension/Diabetes** → GREEN (routine), YELLOW if severe
5. **Chest Pain** → RED (emergency rule), can't miss cardiac
6. **Mental Health (Depression/Anxiety)** → YELLOW, counselor referral
7. **Maternal (Pregnant/Postpartum)** → Danger sign protocol
8. **Fever (non-malaria)** → Differential diagnosis (TB, typhoid)
9. **Skin Infection** → GREEN (topical), YELLOW if spreading
10. **Injury/Trauma** → Severity-based (RED if severe, GREEN if minor)

---

## Deployment Plan

### Frontend
- Deploy to **Vercel** (Next.js)
- Environment: `.env.local` with API_ENDPOINT
- Command: `npm run build && vercel deploy`

### Backend
- Deploy to **Render** (FastAPI Python)
- Port: 8000
- Environment: CLAUDE_API_KEY, ENVIRONMENT=demo
- Command: `pip install -r requirements.txt && uvicorn main:app`

### NVIDIA Brev
- Use for **embeddings** (symptom similarity matching)
- Use for **LLM inference** (Claude API calls via Brev)
- Set up MCP server for health data access (future)

---

## File Structure for Hackathon

```
medi-triage-ai/
├── frontend/                    # React/Next.js
│   ├── package.json
│   ├── pages/
│   ├── components/
│   └── public/
│
├── backend/                     # FastAPI Python
│   ├── main.py                 # FastAPI app + orchestrator
│   ├── agents/
│   │   ├── symptom_analyzer.py    # Agent 1
│   │   ├── triage_router.py       # Agent 2
│   │   └── care_pathway.py        # Agent 3
│   ├── data/
│   │   ├── conditions.db
│   │   ├── triage_rules.json
│   │   └── test_cases.json
│   └── requirements.txt
│
├── docs/
│   ├── TEAM_BRIEF.md
│   ├── TECHNICAL_ARCHITECTURE.md
│   └── API_DOCS.md
│
└── .env.example
```

---

## Success Checklist (MVP)

- [ ] Frontend loads without errors
- [ ] Can input symptoms (text + checkboxes)
- [ ] Backend receives request → processes → returns triage
- [ ] Result displays in <30 seconds
- [ ] Triage decision is color-coded (RED/YELLOW/GREEN)
- [ ] Printable referral slip looks professional
- [ ] Test with 5 patient scenarios
- [ ] NVIDIA Brev integration works
- [ ] Live URL (Vercel) + Backend URL (Render) connected
- [ ] Demo runs smoothly

---

**Built by:** Geofry (Lead), Person 2 (Frontend), Person 3 (Data), Person 4 (DevOps)  
**Timeline:** Sept 25-27, 2026  
**Target:** GOMYCODE Hackathon, Sept 27, 2026
