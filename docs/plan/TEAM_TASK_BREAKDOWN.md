# MediTriage AI - Team Task Breakdown

## Quick Summary

**Project:** MediTriage AI  
**Goal:** Build an AI triage system for Kenya's health clinics  
**Timeline:** Sept 25 (kickoff) → Sept 27 (hackathon demo)  
**Target:** Judges test 5 patient scenarios, get instant RED/YELLOW/GREEN triage + printable referral slip  

---

# PERSON 1: GEOFRY (YOU - LEAD DEVELOPER + DEVOPS)

## Your Role: Build the AI Brain + Ship It Live

You are the **architect**, **backend engineer**, AND **DevOps lead**. You:
1. Coordinate all 4 AI agents + make them work together
2. Handle all deployment (GitHub, Render backend, Vercel frontend, NVIDIA Brev)
3. Make sure Person 2's frontend talks to your backend
4. Own the entire technical stack

### What You're Building

The **Agent Orchestrator** — a Python FastAPI backend that:
1. Receives patient symptoms from the frontend
2. Sends them to Claude API (Agent 1: Symptom Analyzer)
3. Gets structured response, sends to Agent 2 (Triage Router)
4. Gets triage decision, sends to Agent 3 (Care Pathway)
5. Returns final recommendation to frontend

### Deliverables (Due Sept 27, 9 AM)

**Backend:**
- [ ] FastAPI app running on `http://localhost:8000`
- [ ] `/api/analyze-symptoms` endpoint (calls Agent 1)
- [ ] `/api/triage-decision` endpoint (calls Agent 2)
- [ ] `/api/care-pathway` endpoint (calls Agent 3)
- [ ] `/api/full-triage` endpoint (chains all 3 agents)
- [ ] NVIDIA Brev integration (at least LLM calls working)
- [ ] `.env.example` file with all required keys

**DevOps:**
- [ ] GitHub repo set up (push all code here)
- [ ] Backend deployed to Render (live HTTPS URL)
- [ ] Frontend deployed to Vercel (live HTTPS URL)
- [ ] Frontend `.env` connected to Render backend URL
- [ ] Both services tested + working together
- [ ] DEPLOYMENT.md with live URLs documented

**Nice-to-Have:**
- [ ] SMS/USSD fallback logic (pseudocode)
- [ ] Error handling + logging
- [ ] Auto-deploy on GitHub push

### Step-by-Step Implementation Plan

#### **Day 1 (Sept 25) - Setup & Agent 1**

**Morning (2 hours):**
1. Create Python project structure
   ```bash
   mkdir medi-triage-backend
   cd medi-triage-backend
   python -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn anthropic python-dotenv
   ```

2. Create `.env` file
   ```
   CLAUDE_API_KEY=sk-...your-key...
   ENVIRONMENT=development
   ```

3. Create `main.py` with basic FastAPI app
   ```python
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   
   app = FastAPI(title="MediTriage AI")
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000", "your-vercel-url"],
       allow_methods=["*"],
       allow_headers=["*"],
   )
   
   @app.get("/health")
   def health():
       return {"status": "ok"}
   ```

4. Test it runs: `uvicorn main:app --reload`

**Afternoon (3 hours):**
5. Create `agents/symptom_analyzer.py` (Agent 1)
   ```python
   import anthropic
   import json
   
   client = anthropic.Anthropic()
   
   def analyze_symptoms(symptom_text, patient_age, patient_context):
       """Agent 1: Parse patient symptoms into structured data"""
       
       prompt = f"""
       You are a medical AI that helps primary care clinics in Kenya.
       
       Patient Information:
       - Age: {patient_age}
       - Context: {patient_context}
       - Symptoms described: {symptom_text}
       
       Extract the following in JSON format:
       {{
           "primary_symptom": "the main complaint",
           "associated_symptoms": ["symptom2", "symptom3"],
           "duration_days": number,
           "severity": "mild|moderate|severe",
           "red_flags": ["any danger signs"],
           "differential_considerations": ["possible conditions in Kenya context"]
       }}
       
       Be brief. Assume Kenya disease context (malaria, TB, etc).
       """
       
       message = client.messages.create(
           model="claude-opus-5.5",
           max_tokens=500,
           messages=[
               {"role": "user", "content": prompt}
           ]
       )
       
       # Extract JSON from response
       response_text = message.content[0].text
       
       # Parse JSON (Claude should return valid JSON)
       try:
           result = json.loads(response_text)
       except:
           # Fallback if Claude doesn't return clean JSON
           result = {"raw_response": response_text}
       
       return result
   ```

6. Create endpoint for Agent 1
   ```python
   @app.post("/api/analyze-symptoms")
   def endpoint_analyze(request: dict):
       result = analyze_symptoms(
           request["symptoms"],
           request["patient_age"],
           request["patient_context"]
       )
       return result
   ```

7. Test with curl
   ```bash
   curl -X POST http://localhost:8000/api/analyze-symptoms \
     -H "Content-Type: application/json" \
     -d '{
       "symptoms": "I have fever and headache",
       "patient_age": 35,
       "patient_context": {"hiv_status": "negative"}
     }'
   ```

#### **Day 2 (Sept 26) - Agents 2 & 3 + Integration**

**Morning (3 hours):**
8. Create `agents/triage_router.py` (Agent 2 - Rule-Based)
   ```python
   def triage_decision(symptom_profile):
       """Agent 2: Decide RED/YELLOW/GREEN based on symptoms"""
       
       primary = symptom_profile.get("primary_symptom", "").lower()
       red_flags = symptom_profile.get("red_flags", [])
       severity = symptom_profile.get("severity", "mild")
       
       # RED rules (Emergency)
       if "chest pain" in primary or any("difficulty breathing" in str(f).lower() for f in red_flags):
           return {
               "triage_level": "RED",
               "urgency": "EMERGENCY",
               "rationale": "Possible cardiac emergency",
               "recommended_pathway": "hospital"
           }
       
       if "seizure" in str(red_flags).lower() or "unconscious" in str(red_flags).lower():
           return {
               "triage_level": "RED",
               "urgency": "EMERGENCY",
               "rationale": "Severe neurological symptoms",
               "recommended_pathway": "hospital"
           }
       
       # YELLOW rules (Urgent)
       if severity == "severe" and ("fever" in primary or "cough" in primary):
           return {
               "triage_level": "YELLOW",
               "urgency": "URGENT",
               "rationale": "High fever with respiratory symptoms - malaria/pneumonia risk",
               "recommended_pathway": "clinic"
           }
       
       if "fever" in primary and severity in ["moderate", "severe"]:
           return {
               "triage_level": "YELLOW",
               "urgency": "URGENT",
               "rationale": "High fever requires evaluation",
               "recommended_pathway": "clinic"
           }
       
       # GREEN rules (Routine)
       return {
           "triage_level": "GREEN",
           "urgency": "ROUTINE",
           "rationale": "Routine primary care - can be managed at clinic or home",
           "recommended_pathway": "clinic_or_home"
       }
   ```

9. Create endpoint for Agent 2
   ```python
   @app.post("/api/triage-decision")
   def endpoint_triage(request: dict):
       result = triage_decision(request["symptom_profile"])
       return result
   ```

10. Create `agents/care_pathway.py` (Agent 3)
    ```python
    def generate_care_pathway(triage_level, symptom_profile, language="en"):
        """Agent 3: Use Claude to personalize care pathway"""
        
        client = anthropic.Anthropic()
        
        template = {
            "RED": {
                "instruction": "GO TO HOSPITAL IMMEDIATELY",
                "location": "Nearest hospital/sub-county facility",
                "wait_time": "Emergency",
                "cost": "Covered by SHA (Social Health Authority) (bring card)",
                "what_to_bring": ["SHA (Social Health Authority) card", "ID", "Recent medications"]
            },
            "YELLOW": {
                "instruction": "Come to clinic TODAY",
                "location": "This health center",
                "wait_time": "Expect 30-60 mins",
                "cost": "FREE under SHA (Social Health Authority) capitation",
                "home_care": ["Rest", "Hydration", "Monitor temperature"]
            },
            "GREEN": {
                "instruction": "Manage at home, monitor symptoms",
                "location": "No clinic visit needed now",
                "when_to_come": "If symptoms worsen or persist 5+ days",
                "cost": "No cost",
                "self_care": ["Rest", "Hydration", "Light food"]
            }
        }
        
        # Claude personalizes template
        prompt = f"""
        Create a simple, clear care instruction for a patient with:
        Symptoms: {symptom_profile.get('primary_symptom')}
        Triage Level: {triage_level}
        
        Write in simple {language} (6-8 word sentences max).
        Include:
        1. What patient should do immediately
        2. Where to go (or not go)
        3. What to bring
        4. Danger signs to watch for
        
        Make it printable on a clinic referral slip.
        """
        
        message = client.messages.create(
            model="claude-opus-5.5",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "template": template.get(triage_level),
            "personalized_instruction": message.content[0].text,
            "language": language
        }
    ```

11. Create endpoint for Agent 3
    ```python
    @app.post("/api/care-pathway")
    def endpoint_pathway(request: dict):
        result = generate_care_pathway(
            request["triage_level"],
            request["symptom_profile"],
            request.get("language", "en")
        )
        return result
    ```

**Afternoon (3 hours):**
12. Create orchestrator function that chains all 3 agents
    ```python
    @app.post("/api/full-triage")
    def full_triage(request: dict):
        """End-to-end: symptom → triage → care pathway"""
        
        # Step 1: Analyze symptoms
        analysis = analyze_symptoms(
            request["symptoms"],
            request["patient_age"],
            request.get("patient_context", {})
        )
        
        # Step 2: Get triage decision
        triage = triage_decision(analysis)
        
        # Step 3: Generate care pathway
        pathway = generate_care_pathway(
            triage["triage_level"],
            analysis,
            request.get("language", "en")
        )
        
        return {
            "symptom_analysis": analysis,
            "triage": triage,
            "care_pathway": pathway,
            "timestamp": datetime.now().isoformat()
        }
    ```

13. Set up test cases file `data/test_cases.json`
    ```json
    {
      "test_cases": [
        {
          "name": "Malaria Case",
          "symptoms": "High fever, chills, headache, body aches",
          "patient_age": 25,
          "expected_triage": "YELLOW"
        },
        {
          "name": "Chest Pain",
          "symptoms": "Severe chest pain, shortness of breath",
          "patient_age": 50,
          "expected_triage": "RED"
        }
      ]
    }
    ```

14. Deploy to Render
    - Create `requirements.txt`
      ```
      fastapi==0.104.0
      uvicorn==0.24.0
      anthropic==0.7.0
      python-dotenv==1.0.0
      ```
    - Push to GitHub
    - Connect Render → auto-deploy on push
    - Add `CLAUDE_API_KEY` to Render environment

#### **Day 2 Cont. (Sept 26 Evening) - Deployment**

14. Deploy backend to Render
    - Push backend code to GitHub
    - Create Render.com account (or sign in)
    - Connect GitHub repo to Render
    - Set build command: `pip install -r requirements.txt`
    - Set start command: `uvicorn main:app --host 0.0.0.0 --port 8000`
    - Add `CLAUDE_API_KEY` environment variable
    - Deploy and get live URL

15. Deploy frontend to Vercel
    - Push frontend code to GitHub
    - Create Vercel account (or sign in)
    - Import frontend repo
    - Set `NEXT_PUBLIC_API_URL` to your Render backend URL
    - Deploy and get live URL

16. Set up NVIDIA Brev (if needed for speed optimization)
    - Link Claude API calls through Brev for inference
    - Test one API call through Brev

#### **Day 3 (Sept 27 Morning) - Final Testing**

17. Test all 5 scenarios end-to-end with live URLs
18. Make sure response time is <30 seconds
19. Check error messages are user-friendly
20. Verify both Render (backend) and Vercel (frontend) are working
21. Document live URLs in DEPLOYMENT.md

---

# PERSON 2: FRONTEND DEVELOPER

## Your Role: Build the App Interface

You create the **user interface** that patients/nurses use. Make it beautiful, simple, and mobile-first.

### What You're Building

A **React/Next.js web app** with:
1. **Intake Form** → Collect patient symptoms
2. **Results Display** → Show RED/YELLOW/GREEN triage
3. **Referral Slip** → Printable output

### Deliverables (Due Sept 27, 9 AM)

**Must-Have:**
- [ ] Home page with clear instructions
- [ ] Symptom input form (checkboxes + free text)
- [ ] Results page with color-coded display (RED=red, YELLOW=yellow, GREEN=green)
- [ ] Printable referral slip
- [ ] Connected to backend API (Geofry's Render URL)
- [ ] Deployed to Vercel (live URL)
- [ ] Mobile-responsive (works on phone screens)

**Nice-to-Have:**
- [ ] Swahili language toggle
- [ ] Loading spinner while waiting for API
- [ ] Error messages if API fails

### Step-by-Step Implementation Plan

#### **Day 1 (Sept 25) - Setup & Layout**

**Morning (2 hours):**
1. Create Next.js project
   ```bash
   npx create-next-app@latest medi-triage-frontend --typescript=no
   cd medi-triage-frontend
   npm run dev
   ```

2. Create `.env.local`
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   (Will change to Render URL later)

3. Delete default Next.js boilerplate files

4. Create folder structure
   ```
   src/
   ├── components/
   ├── pages/
   ├── styles/
   └── utils/
   ```

**Afternoon (3 hours):**
5. Create `pages/index.jsx` (Home page)
   ```jsx
   export default function Home() {
     return (
       <div className="container">
         <h1>MediTriage AI</h1>
         <p>Smart healthcare triage for Kenya's clinics</p>
         
         <div className="instructions">
           <h2>How it works:</h2>
           <ol>
             <li>Describe your symptoms</li>
             <li>AI decides urgency (RED/YELLOW/GREEN)</li>
             <li>Get instructions where to go</li>
             <li>Print referral slip</li>
           </ol>
         </div>
         
         <a href="/triage" className="btn btn-primary">
           Start Triage
         </a>
       </div>
     )
   }
   ```

6. Create `pages/triage.jsx` (Main triage form page)
   ```jsx
   import { useState } from 'react'
   
   export default function TriagePage() {
     const [step, setStep] = useState(1)
     const [formData, setFormData] = useState({
       symptoms: "",
       patient_age: "",
       patient_context: {}
     })
     const [result, setResult] = useState(null)
     const [loading, setLoading] = useState(false)
     
     const handleSubmit = async () => {
       setLoading(true)
       try {
         const response = await fetch(
           `${process.env.NEXT_PUBLIC_API_URL}/api/full-triage`,
           {
             method: "POST",
             headers: { "Content-Type": "application/json" },
             body: JSON.stringify(formData)
           }
         )
         const data = await response.json()
         setResult(data)
         setStep(2)  // Move to results page
       } catch (error) {
         alert("Error: " + error.message)
       }
       setLoading(false)
     }
     
     if (step === 1) {
       return (
         <div className="triage-form">
           <h1>Patient Assessment</h1>
           
           <div className="form-group">
             <label>Age:</label>
             <input
               type="number"
               value={formData.patient_age}
               onChange={(e) => setFormData({...formData, patient_age: e.target.value})}
               min="0"
               max="120"
             />
           </div>
           
           <div className="form-group">
             <label>Describe symptoms (in your own words):</label>
             <textarea
               value={formData.symptoms}
               onChange={(e) => setFormData({...formData, symptoms: e.target.value})}
               placeholder="E.g., 'I have high fever, headache, and body aches...'"
               rows="5"
             />
           </div>
           
           <div className="form-group">
             <label>
               <input
                 type="checkbox"
                 onChange={(e) => setFormData({
                   ...formData,
                   patient_context: {
                     ...formData.patient_context,
                     hiv_positive: e.target.checked
                   }
                 })}
               />
               HIV-positive
             </label>
           </div>
           
           <button onClick={handleSubmit} disabled={loading} className="btn btn-primary">
             {loading ? "Analyzing..." : "Get Triage Decision"}
           </button>
         </div>
       )
     }
     
     if (step === 2 && result) {
       return <ResultsPage result={result} />
     }
   }
   
   function ResultsPage({ result }) {
     const triage = result.triage
     const bgColor = {
       RED: "#ff4444",
       YELLOW: "#ffbb33",
       GREEN: "#00C851"
     }
     
     return (
       <div className="results-page">
         <div className="triage-card" style={{ backgroundColor: bgColor[triage.triage_level] }}>
           <h1>{triage.triage_level}</h1>
           <h2>{triage.urgency}</h2>
           <p>{triage.rationale}</p>
         </div>
         
         <div className="pathway-card">
           <h3>What to do:</h3>
           <p>{result.care_pathway.personalized_instruction}</p>
         </div>
         
         <button onClick={() => window.print()} className="btn btn-secondary">
           Print Referral Slip
         </button>
       </div>
     )
   }
   ```

7. Create `styles/globals.css` (Basic styling)
   ```css
   * {
     margin: 0;
     padding: 0;
     box-sizing: border-box;
   }
   
   body {
     font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
     line-height: 1.6;
     color: #333;
     background: #f5f5f5;
   }
   
   .container {
     max-width: 600px;
     margin: 0 auto;
     padding: 20px;
     background: white;
     border-radius: 8px;
     box-shadow: 0 2px 8px rgba(0,0,0,0.1);
   }
   
   h1 { font-size: 2em; margin: 20px 0; }
   h2 { font-size: 1.5em; margin: 15px 0; }
   h3 { font-size: 1.2em; margin: 10px 0; }
   
   .btn {
     padding: 12px 24px;
     font-size: 1em;
     border: none;
     border-radius: 4px;
     cursor: pointer;
     transition: all 0.2s;
   }
   
   .btn-primary {
     background: #0066cc;
     color: white;
   }
   
   .btn-primary:hover {
     background: #0052a3;
   }
   
   .form-group {
     margin: 15px 0;
   }
   
   .form-group label {
     display: block;
     margin-bottom: 5px;
     font-weight: bold;
   }
   
   .form-group input,
   .form-group textarea {
     width: 100%;
     padding: 8px;
     border: 1px solid #ddd;
     border-radius: 4px;
     font-size: 1em;
   }
   
   .triage-card {
     padding: 30px;
     border-radius: 8px;
     color: white;
     text-align: center;
     margin: 20px 0;
   }
   
   .triage-card h1 {
     font-size: 3em;
     margin: 10px 0;
   }
   
   .pathway-card {
     background: #f9f9f9;
     padding: 20px;
     border-left: 4px solid #0066cc;
     margin: 20px 0;
   }
   
   /* Mobile responsive */
   @media (max-width: 600px) {
     .container {
       padding: 10px;
     }
     h1 { font-size: 1.5em; }
     .triage-card h1 { font-size: 2.5em; }
   }
   ```

#### **Day 2 (Sept 26) - Polish & Integration**

8. Add Swahili support (optional)
   - Create `utils/translations.js`
   - Add language toggle on home page

9. Add loading spinner
   ```jsx
   {loading && <div className="spinner">Analyzing...</div>}
   ```

10. Test form submission with Geofry's localhost backend
    - Update `.env.local` to use `http://localhost:8000`
    - Submit test case, verify results display correctly

11. Create printable referral slip component
    ```jsx
    import { useRef } from 'react'
    
    function ReferralSlip({ result }) {
      const printRef = useRef()
      
      return (
        <>
          <div ref={printRef} className="referral-slip">
            <h1>CLINIC REFERRAL SLIP</h1>
            <div className="slip-content">
              <p><strong>Date:</strong> {new Date().toLocaleDateString()}</p>
              <p><strong>Triage Level:</strong> <span className="triage-badge">{result.triage.triage_level}</span></p>
              <p><strong>Assessment:</strong> {result.triage.rationale}</p>
              <p><strong>Instructions:</strong></p>
              <p>{result.care_pathway.personalized_instruction}</p>
            </div>
          </div>
          <button onClick={() => window.print()}>Print</button>
        </>
      )
    }
    ```

12. Deploy to Vercel
    - Push to GitHub
    - Connect Vercel project
    - Update `.env.local` with Render backend URL once live

#### **Day 3 (Sept 27 Morning) - Final Testing**

13. Test on mobile phone (use Chrome DevTools)
14. Test all 5 scenarios with Geofry
15. Make sure print function works
16. Verify Vercel deployment is live

---

# PERSON 3: DATA & CONTENT SPECIALIST

## Your Role: Create the Knowledge Base

You prepare all the **disease data** and **test scenarios** that power the triage decisions.

### What You're Building

1. **Condition Database** — 10 Kenyan health conditions + their symptoms
2. **Triage Rules** — Decision logic (what makes something RED vs YELLOW vs GREEN)
3. **Test Cases** — 5 realistic patient scenarios for hackathon demo

### Deliverables (Due Sept 26 EOD)

**Must-Have:**
- [ ] `conditions.json` — 10 conditions with symptoms, red flags, treatment location, SHA (Social Health Authority) cost
- [ ] `triage_rules.json` — Decision rules (condition + context → RED/YELLOW/GREEN)
- [ ] `test_cases.json` — 5 test patient scenarios with expected triage level
- [ ] Kenya-accurate disease burden data (cite sources)
- [ ] Swahili translations for top 20 symptoms + instructions

**Nice-to-Have:**
- [ ] SHA (Social Health Authority) benefit coverage database
- [ ] Regional variation (Kisumu vs Nairobi conditions)
- [ ] CDC/WHO Kenya guidelines references

### Step-by-Step Implementation Plan

#### **Day 1 (Sept 25)**

1. Create `data/conditions.json`
   ```json
   {
     "conditions": [
       {
         "id": 1,
         "name": "Malaria",
         "swahili_name": "Malaria",
         "prevalence_rank": 1,
         "description": "Parasitic infection transmitted by mosquitoes",
         "typical_age_group": "All ages",
         "symptoms": [
           "Fever (38-40°C)",
           "Chills/shaking",
           "Headache",
           "Body aches",
           "Nausea/vomiting",
           "Fatigue"
         ],
         "red_flag_indicators": [
           "Fever >40°C",
           "Confusion/altered mental status",
           "Seizures",
           "Severe vomiting",
           "Rapid breathing"
         ],
         "treatment_location": "clinic or hospital (if severe)",
         "estimated_cost": "0-500 KES",
         "nhif_covered": true,
         "self_care": [
           "Rest",
           "Drink plenty of water",
           "Take paracetamol for pain/fever",
           "Avoid going out until fever subsides"
         ],
         "danger_signs_watch": [
           "Worsening confusion",
           "Difficulty breathing",
           "Black urine",
           "Severe abdominal pain"
         ]
       },
       {
         "id": 2,
         "name": "Respiratory Infection",
         "swahili_name": "Ugonjwa wa kupumzika",
         "prevalence_rank": 2,
         "description": "Upper/lower respiratory tract infection (cold, flu, bronchitis)",
         "symptoms": [
           "Cough",
           "Sore throat",
           "Runny/blocked nose",
           "Fever (low-grade)",
           "Fatigue",
           "Mild headache"
         ],
         "red_flag_indicators": [
           "Severe shortness of breath",
           "Chest pain",
           "High fever (>39°C)",
           "Coughing up blood",
           "Symptoms >2 weeks (TB suspicion)"
         ],
         "treatment_location": "home or clinic",
         "estimated_cost": "0-300 KES",
         "nhif_covered": true,
         "self_care": [
           "Rest",
           "Gargle with salt water",
           "Honey/ginger tea",
           "Steam inhalation",
           "Avoid smoke/pollution"
         ]
       },
       {
         "id": 3,
         "name": "Hypertension",
         "swahili_name": "Uzamili wa damu",
         "prevalence_rank": 3,
         "description": "High blood pressure, often chronic",
         "symptoms": [
           "Headache",
           "Dizziness",
           "Chest discomfort",
           "Shortness of breath",
           "Often asymptomatic"
         ],
         "red_flag_indicators": [
           "Systolic >180 mmHg",
           "Chest pain",
           "Confusion/vision changes",
           "Difficulty breathing"
         ],
         "treatment_location": "clinic (routine monitoring)",
         "estimated_cost": "0 (free at dispensary)",
         "nhif_covered": true,
         "self_care": [
           "Reduce salt intake",
           "Regular exercise",
           "Weight management",
           "Stress reduction",
           "Take medications as prescribed"
         ]
       },
       {
         "id": 4,
         "name": "Diarrhea/Gastroenteritis",
         "swahili_name": "Kuvimba kinywa",
         "prevalence_rank": 4,
         "description": "Intestinal infection causing loose stools",
         "symptoms": [
           "Loose/watery stools",
           "Abdominal cramps",
           "Nausea",
           "Vomiting",
           "Mild fever"
         ],
         "red_flag_indicators": [
           "Severe dehydration (dizziness, dry mouth)",
           "Blood in stool",
           "Severe abdominal pain",
           "Persistent vomiting",
           "High fever"
         ],
         "treatment_location": "home (unless dehydrated)",
         "estimated_cost": "0-200 KES",
         "nhif_covered": true,
         "self_care": [
           "Oral rehydration (salt + sugar solution)",
           "Small frequent meals",
           "Avoid dairy",
           "Wash hands frequently",
           "Boil drinking water"
         ]
       },
       {
         "id": 5,
         "name": "Chest Pain",
         "swahili_name": "Maumau ya kini",
         "prevalence_rank": 5,
         "description": "Pain/discomfort in chest - potential cardiac",
         "symptoms": [
           "Sharp/dull chest pain",
           "Pressure sensation",
           "Pain radiating to arm/jaw",
           "Shortness of breath"
         ],
         "red_flag_indicators": [
           "Any chest pain + shortness of breath = EMERGENCY",
           "Sweating + chest pain",
           "Rapid heart rate",
           "Severe, sudden onset",
           "Pain at rest"
         ],
         "treatment_location": "HOSPITAL IMMEDIATELY",
         "estimated_cost": "May need ECG/cardiac workup",
         "nhif_covered": true,
         "self_care": [
           "STOP ALL ACTIVITY",
           "Sit down, remain calm",
           "Chew aspirin (325mg) if available",
           "Call ambulance immediately"
         ]
       },
       {
         "id": 6,
         "name": "Depression/Anxiety",
         "swahili_name": "Kupoteza moyo/Wasiwasi",
         "prevalence_rank": 6,
         "description": "Mental health conditions affecting mood/anxiety",
         "symptoms": [
           "Persistent sadness",
           "Loss of interest",
           "Sleep disturbance",
           "Fatigue",
           "Anxiety/panic",
           "Suicidal thoughts"
         ],
         "red_flag_indicators": [
           "Suicidal ideation",
           "Severe self-harm urges",
           "Complete social withdrawal",
           "Inability to care for self"
         ],
         "treatment_location": "counselor/mental health worker",
         "estimated_cost": "0 (free counseling often available)",
         "nhif_covered": true,
         "self_care": [
           "Talk to trusted person",
           "Regular exercise",
           "Meditation/prayer",
           "Avoid alcohol/drugs",
           "Seek professional counseling"
         ]
       },
       {
         "id": 7,
         "name": "Urinary Tract Infection (UTI)",
         "swahili_name": "Ugonjwa wa mkojo",
         "prevalence_rank": 7,
         "description": "Infection of bladder/urethra",
         "symptoms": [
           "Pain/burning during urination",
           "Frequent urination",
           "Cloudy/dark urine",
           "Mild lower abdominal pain",
           "Low-grade fever"
         ],
         "red_flag_indicators": [
           "Fever + back pain (kidney infection)",
           "Blood in urine",
           "Severe abdominal pain"
         ],
         "treatment_location": "clinic (may need antibiotics)",
         "estimated_cost": "200-500 KES",
         "nhif_covered": true,
         "self_care": [
           "Drink plenty of water",
           "Urinate frequently",
           "Avoid caffeine",
           "Cranberry juice (if available)",
           "Avoid sexual activity until treated"
         ]
       },
       {
         "id": 8,
         "name": "Skin Infection",
         "swahili_name": "Ugonjwa wa ngozi",
         "prevalence_rank": 8,
         "description": "Bacterial/fungal skin infection",
         "symptoms": [
           "Red/inflamed area",
           "Itching",
           "Pustules/oozing",
           "Swollen area",
           "Localized pain"
         ],
         "red_flag_indicators": [
           "Rapid spreading",
           "Red streaks going up limb",
           "Fever + skin infection",
           "Large area affected"
         ],
         "treatment_location": "clinic (for antibiotics if needed)",
         "estimated_cost": "200-500 KES",
         "nhif_covered": true,
         "self_care": [
           "Keep area clean",
           "Avoid touching/scratching",
           "Use topical antibiotic if available",
           "Keep covered if draining",
           "Wash hands after touching"
         ]
       },
       {
         "id": 9,
         "name": "Diabetes",
         "swahili_name": "Sukari",
         "prevalence_rank": 9,
         "description": "Chronic endocrine disorder affecting blood sugar",
         "symptoms": [
           "Increased thirst",
           "Frequent urination",
           "Fatigue",
           "Blurred vision",
           "Often asymptomatic"
         ],
         "red_flag_indicators": [
           "Diabetic ketoacidosis (fruity breath, severe nausea)",
           "Extremely high/low blood sugar symptoms",
           "Sudden vision loss",
           "Severe infection (foot ulcer)"
         ],
         "treatment_location": "clinic (routine monitoring)",
         "estimated_cost": "0 (free monitoring + insulin at dispensary)",
         "nhif_covered": true,
         "self_care": [
           "Regular blood sugar monitoring",
           "Healthy diet (low sugar)",
           "Regular exercise",
           "Medication adherence",
           "Foot care (check daily)"
         ]
       },
       {
         "id": 10,
         "name": "Minor Injury/Trauma",
         "swahili_name": "Jeraha",
         "prevalence_rank": 10,
         "description": "Cuts, bruises, minor wound injuries",
         "symptoms": [
           "Bleeding",
           "Bruising",
           "Swelling",
           "Pain",
           "Possible foreign object"
         ],
         "red_flag_indicators": [
           "Severe bleeding that won't stop",
           "Deep cut requiring stitches",
           "Signs of infection (warmth, pus)",
           "Signs of fracture",
           "Tetanus risk (dirty/rusty object)"
         ],
         "treatment_location": "home (or clinic if serious)",
         "estimated_cost": "0-500 KES",
         "nhif_covered": true,
         "self_care": [
           "Clean with soap/clean water",
           "Apply pressure if bleeding",
           "Elevate if swelling",
           "Apply antibiotic ointment",
           "Cover with clean bandage",
           "Watch for signs of infection"
         ]
       }
     ]
   }
   ```

2. Create `data/triage_rules.json`
   ```json
   {
     "rules": [
       {
         "rule_id": "r001",
         "name": "Cardiac Emergency",
         "triggers": [
           "primary_symptom_contains: chest_pain",
           "AND associated_symptom_contains: difficulty_breathing"
         ],
         "triage_level": "RED",
         "rationale": "Possible cardiac emergency"
       },
       {
         "rule_id": "r002",
         "name": "High Fever + Respiratory",
         "triggers": [
           "primary_symptom_contains: fever",
           "AND severity: severe",
           "AND associated_symptom_contains: cough"
         ],
         "triage_level": "YELLOW",
         "rationale": "High fever with respiratory symptoms - malaria/pneumonia risk"
       },
       {
         "rule_id": "r003",
         "name": "Suicidal Ideation",
         "triggers": [
           "red_flags_contain: suicidal"
         ],
         "triage_level": "RED",
         "rationale": "Mental health emergency - immediate counselor referral"
       },
       {
         "rule_id": "r004",
         "name": "Routine UTI",
         "triggers": [
           "primary_symptom_contains: dysuria",
           "severity: mild_moderate",
           "no_red_flags"
         ],
         "triage_level": "GREEN",
         "rationale": "Routine UTI - clinic visit, likely needs antibiotics"
       },
       {
         "rule_id": "r005",
         "name": "Default Routine",
         "triggers": [
           "no_red_flags",
           "severity: mild_moderate"
         ],
         "triage_level": "GREEN",
         "rationale": "Routine primary care"
       }
     ]
   }
   ```

3. Create `data/test_cases.json`
   ```json
   {
     "test_cases": [
       {
         "scenario_id": 1,
         "patient_name": "Test Case 1: Malaria",
         "patient_age": 25,
         "symptoms": "I have been having high fever for 2 days, with chills, severe headache, and my whole body aches. I also feel nauseous.",
         "patient_context": {
           "hiv_status": "negative",
           "pregnant": false,
           "chronic_conditions": []
         },
         "expected_triage_level": "YELLOW",
         "expected_rationale": "High fever + headache + body aches = malaria suspicion (endemic in Kenya). Requires urgent clinic evaluation.",
         "expected_pathway": "Come to clinic today for malaria rapid test and treatment. Free under SHA (Social Health Authority)."
       },
       {
         "scenario_id": 2,
         "patient_name": "Test Case 2: Routine Hypertension Check",
         "patient_age": 55,
         "symptoms": "My blood pressure monitor at home shows 135/85. I'm on blood pressure medication but want to check if I'm doing well.",
         "patient_context": {
           "hiv_status": "negative",
           "pregnant": false,
           "chronic_conditions": ["hypertension"]
         },
         "expected_triage_level": "GREEN",
         "expected_rationale": "Routine hypertension monitoring. Blood pressure mildly elevated but stable on medication.",
         "expected_pathway": "Routine clinic visit. No emergency. Blood pressure is controlled. Continue medication as prescribed. Free visit under SHA (Social Health Authority)."
       },
       {
         "scenario_id": 3,
         "patient_name": "Test Case 3: Severe Chest Pain (EMERGENCY)",
         "patient_age": 52,
         "symptoms": "I have severe chest pain, it feels like pressure, and I'm having trouble breathing. I'm sweating and my heart is racing.",
         "patient_context": {
           "hiv_status": "negative",
           "pregnant": false,
           "chronic_conditions": ["hypertension", "diabetes"]
         },
         "expected_triage_level": "RED",
         "expected_rationale": "Chest pain + difficulty breathing + sweating = CARDIAC EMERGENCY. Do not wait.",
         "expected_pathway": "GO TO HOSPITAL IMMEDIATELY. Call ambulance if available. Chew aspirin. This is a life-threatening emergency."
       },
       {
         "scenario_id": 4,
         "patient_name": "Test Case 4: Depression with Suicidal Thoughts (MENTAL HEALTH EMERGENCY)",
         "patient_age": 28,
         "symptoms": "I've been sad for weeks, I've lost interest in everything, I can't sleep, and I keep thinking about harming myself. I don't see the point anymore.",
         "patient_context": {
           "hiv_status": "negative",
           "pregnant": false,
           "chronic_conditions": []
         },
         "expected_triage_level": "RED",
         "expected_rationale": "Severe depression with suicidal ideation. Mental health emergency requiring immediate intervention.",
         "expected_pathway": "Contact mental health counselor/psychologist immediately. If in crisis, call national mental health hotline. Do not leave patient alone."
       },
       {
         "scenario_id": 5,
         "patient_name": "Test Case 5: Common Cold (Routine)",
         "patient_age": 8,
         "symptoms": "My child has a runny nose, mild cough, and a little bit of fever (37.5°C). He's still playing but a bit tired.",
         "patient_context": {
           "hiv_status": "negative",
           "pregnant": false,
           "chronic_conditions": []
         },
         "expected_triage_level": "GREEN",
         "expected_rationale": "Mild upper respiratory infection (common cold). Self-limiting, routine care.",
         "expected_pathway": "Manage at home. Rest, fluids, honey/ginger tea. Mild fever is normal immune response. Watch for danger signs (severe breathing difficulty). Seek clinic care if symptoms worsen after 5 days."
       }
     ]
   }
   ```

4. Create `data/swahili_translations.json`
   ```json
   {
     "symptoms": {
       "fever": "Moto",
       "headache": "Maumivu ya kichwa",
       "cough": "Kikohozi",
       "shortness_of_breath": "Kushindwa kupumua",
       "chest_pain": "Maumau ya moyo/kini",
       "diarrhea": "Kuvimba",
       "nausea": "Mtindi",
       "fatigue": "Kuchoka",
       "depression": "Kupoteza moyo",
       "anxiety": "Wasiwasi",
       "difficulty_urinating": "Kutokutaka mkojo haraka"
     },
     "instructions": {
       "go_to_hospital": "Kwenda hospitalini mara moja (HARAKA!)",
       "go_to_clinic": "Kwenda kliniki leo",
       "home_care": "Kustay nyumbani na kujaga dalili",
       "drink_water": "Kunywa maji mengi",
       "rest": "Kupumzika",
       "cost_free": "Ni bure (chini ya SHA (Social Health Authority))",
       "bring_card": "Leta SHA (Social Health Authority) card"
     }
   }
   ```

5. Document data sources
   - Create `data/SOURCES.md`
   ```markdown
   # Data Sources

   ## Disease Burden & Prevalence
   - Kenya Disease Burden Study 2024
   - WHO Country Health Profile - Kenya
   - SHA (Social Health Authority) Disease Statistics 2024
   - Kenya Ministry of Health surveillance reports

   ## Triage Guidelines
   - Kenya National Clinical Guidelines (Primary Care)
   - WHO Emergency Triage Assessment Treatment (ETAT)
   - SHA (Social Health Authority) Capitation Guidelines

   ## Symptoms & Differential Diagnosis
   - CDC Primary Care Reference
   - WHO Integrated Management of Neonatal and Childhood Illness (IMNCI) guidelines adapted for adult care

   ## Cost Data
   - SHA (Social Health Authority) Capitation Handbook
   - Kenya Facility Pricing Survey 2024
   ```

#### **Day 2 (Sept 26)**

6. Review & quality check
   - Verify all 10 conditions have symptoms + red flags
   - Ensure test cases are realistic
   - Add variations (different ages, comorbidities)

7. Create `data/nhif_benefits.json`
   ```json
   {
     "benefits": [
       {
         "facility_level": "dispensary",
         "services": ["Basic consultation", "Basic lab tests", "First aid"],
         "patient_cost": "0 KES",
         "nhif_covers": true
       },
       {
         "facility_level": "health_center",
         "services": ["Consultation", "Lab tests", "Injections", "Maternal care"],
         "patient_cost": "0 KES",
         "nhif_covers": true
       },
       {
         "facility_level": "hospital_referral",
         "services": ["Inpatient care", "Surgery", "Imaging"],
         "patient_cost": "varies (may need payment)",
         "nhif_covers": true
       }
     ]
   }
   ```

---

# PERSON 4: CLINICAL/PRODUCT RESEARCH SPECIALIST

## Your Role: Validate the Problem & Plan for Scale

You ensure we're **solving a real problem** in the **real way Kenya's clinics work**. Your research validates our assumptions and positions us for post-hackathon success.

### What You're Doing

1. **Clinic Workflow Research** — How do nurses actually triage today?
2. **Validation** — Does our triage approach match real clinic needs?
3. **User Testing Plan** — What to ask health workers about the prototype?
4. **Post-Hackathon Roadmap** — How to partner with Ministry of Health?

### Deliverables (Due Sept 27, 9 AM)

**Research Documents:**
- [ ] **Clinic Workflow Document** (2-3 pages)
  - Current triage process at a typical clinic
  - How many patients per day?
  - What causes bottlenecks?
  - Where does our system fit?
  
- [ ] **Validation Checklist** (1 page)
  - Our triage rules match Kenya's clinical guidelines? ✓/✗
  - Our conditions are the top 10 clinic complaints? ✓/✗
  - Our cost assumptions (SHA (Social Health Authority)) are accurate? ✓/✗
  - RED/YELLOW/GREEN logic makes sense to health workers? ✓/✗

- [ ] **User Testing Script** (1 page)
  - 5-7 questions to ask health workers about the demo
  - What would make this useful vs. annoying?
  - Would they actually use this if deployed tomorrow?
  
- [ ] **Post-Hackathon Roadmap** (1 page)
  - How to apply for Kenya's Digital Health Agency regulatory sandbox
  - Which Ministry of Health contacts to reach out to?
  - How to pitch a 5-10 clinic pilot?
  - Timeline + resource requirements

**Demo Materials:**
- [ ] 2-3 talking points about the Kenya context
  - Why this problem is real (backed by your research)
  - Why our approach works (validated with clinic workflows)
  - How to scale after hackathon (regulatory pathway + partnerships)

### Step-by-Step Implementation Plan

#### **Day 1 (Sept 25) - Research & Document**

**Morning (2 hours):**
1. Interview a health worker or clinic manager (if possible)
   - Call someone you know in healthcare (nurse, clinical officer, clinic manager)
   - Ask: "Walk me through your morning triage process"
   - Take notes on:
     - How many patients do you see?
     - How do you decide who is urgent vs. routine?
     - What usually causes delays?
     - What would help you triage faster?

2. If can't reach anyone, use your own observation:
   - Recall a visit to a Kenyan clinic (any visit counts)
   - Document what you saw
   - Research online (WHO docs, Kenya MOH triage guidelines)

**Afternoon (3 hours):**
3. Write **Clinic Workflow Document**
   ```
   EXAMPLE STRUCTURE:
   
   # Current Clinic Triage Process (Kenya Context)
   
   ## Setting
   - Typical urban clinic in Nairobi/Kisumu
   - 2-3 health workers
   - 50-80 patients per day
   - ~3 hours for clinic sessions
   
   ## Current Triage Method
   1. Patient arrives, sits in waiting area
   2. Nurse calls patients in order (first come, first seen)
   3. Nurse quickly asks: "What's wrong?"
   4. Nurse decides: Send to doctor, give medication, refer to hospital
   5. Problem: Urgent cases sometimes wait because of patient ordering
   
   ## Where Our System Fits
   - MediTriage can pre-screen patients at arrival
   - Prioritize urgent cases (RED) to see first
   - Reduce wait time for routine (GREEN) cases
   - Give clear referral instructions (reduce unnecessary hospital trips)
   
   ## Key Success Metrics
   - Reduces wait time for RED cases from 2 hours → 30 min
   - Reduces unnecessary referrals (GREEN cases going home instead of hospital)
   - Saves clinic staff ~1 hour per day on triage decisions
   ```

4. Create **Validation Checklist**
   ```
   CHECKLIST:
   
   ✓ Our triage rules match Kenya's clinical guidelines?
     [ ] Malaria rapid test available at dispensary level?
     [ ] Chest pain truly requires hospital referral (not primary care)?
     [ ] Depression counseling available at clinic level?
   
   ✓ Our top 10 conditions match clinic reality?
     [ ] Malaria is 13-15% of visits (VERIFIED)
     [ ] UTI is common in primary care? (NEEDS VERIFICATION)
     [ ] Mental health referrals available? (NEEDS VERIFICATION)
   
   ✓ Our cost assumptions accurate?
     [ ] SHA (Social Health Authority) truly free at dispensary? (Geofry: verify SHA (Social Health Authority) capitation rules)
     [ ] Referral to hospital costs ~KES 1500? (NEEDS VERIFICATION)
   ```

#### **Day 2 (Sept 26) - Finalize Research**

5. Write **User Testing Script**
   ```
   SCRIPT EXAMPLE:
   
   # Testing MediTriage with Health Workers
   
   After demo, ask health worker:
   
   1. "If a patient walked in right now with these symptoms, 
      would you send them to hospital or see them here?"
      (Compare their answer to our triage)
   
   2. "Would you actually use this if it was on your clinic tablet?"
   
   3. "What would make it MORE useful?"
   
   4. "What would be annoying about it?"
   
   5. "Could this help reduce patient waiting time?"
   ```

6. Write **Post-Hackathon Roadmap**
   ```
   ROADMAP:
   
   ## Regulatory Sandbox (Week 1-2)
   - Contact: Digital Health Agency (DHA), Kenya
   - Document: Clinical validation data
   - Timeline: Sandbox approval 4-8 weeks
   
   ## Pilot Partnership (Month 1-3)
   - Target: 5-10 clinics (partner with AMPATH or Moi University)
   - Train: Health workers on system
   - Collect: Feedback + usage data
   
   ## Funding (Month 1-3)
   - Health tech grants (Global Fund, Gates Foundation)
   - Impact investors (Africa health ventures)
   - Ministry partnership funds
   
   ## Scale (Month 6-12)
   - Roll out to county PCN network (100+ facilities)
   - Integrate with Taifa Care platform
   ```

**Afternoon (2 hours):**
7. Prepare **Demo Talking Points**
   - "In Kenya, nurses see 50-80 patients per day with minimal support"
   - "No standardized triage → urgent cases wait, routine cases clog hospitals"
   - "Our system: patient describes symptoms, AI says RED/YELLOW/GREEN in 30 seconds"
   - "After hackathon: pilot with Ministry of Health, then scale to 100+ facilities"

#### **Day 3 (Sept 27 Morning) - Demo Support**

8. Print out research documents to hand to judges
   - Clinic workflow (shows you understand Kenya context)
   - Validation checklist (shows rigorous thinking)
   - Post-hackathon roadmap (shows sustainability vision)

9. Be on the team call during demo
   - Field questions about Kenya healthcare context
   - Answer: "Why is this problem real in Kenya?"
   - Answer: "How will you validate with real clinics?"
   - Provide talking points for Geofry/Person 2 if they need them

11. Deploy frontend to Vercel
    - Push frontend code to GitHub
    - Vercel auto-deploys on push
    - Get live URL (should be something like `https://medi-triage.vercel.app`)

12. Test end-to-end
    - Open Vercel URL in browser
    - Fill out form with test symptoms
    - Click submit
    - Should return triage decision in <30 seconds

#### **Day 3 (Sept 27 Morning) - Final Checks**

13. Health check both services
    - Backend: `curl https://medi-triage-backend.onrender.com/health`
    - Frontend: Open in browser, verify loads

14. Test all 5 scenarios on live site

15. Document URLs
    - Create `DEPLOYMENT.md`
    ```markdown
    # Live Deployment

    ## Frontend
    - URL: https://medi-triage.vercel.app
    - Built with: Next.js, React
    - Deployed to: Vercel

    ## Backend
    - URL: https://medi-triage-backend.onrender.com
    - Built with: FastAPI, Python
    - Deployed to: Render
    - Health check: https://medi-triage-backend.onrender.com/health

    ## Demo Access
    - Go to: https://medi-triage.vercel.app
    - Click "Start Triage"
    - Enter patient symptoms
    - Get RED/YELLOW/GREEN result
    ```

16. Prepare demo script for judges
    - Write down 3-4 key talking points
    - Practice clicking through demo in 2 minutes

---

## SYNC POINTS (All Team Members)

### **Sept 25, 2 PM - Kickoff**
- Everyone has GitHub repo access
- Everyone has `.env` template
- Geofry explains architecture one more time

### **Sept 26, 6 PM - Integration Test**
- Person 2 (Frontend) connects to Person 1 (Backend) localhost
- Person 3 (Data) provides test cases to Person 2
- Person 4 (DevOps) confirms Render/Vercel accounts working
- Quick test of one scenario end-to-end

### **Sept 27, 7 AM - Final Integration**
- All code merged to main branch
- Both deployments live
- All 5 test scenarios prepped and tested
- Demo URL working

### **Sept 27, 8:45 AM - Pre-Demo**
- Everyone on Zoom/call
- Quick rehearsal of demo (2 min)
- Confirm all systems ready
- Have backup plan if something breaks

---

## Success = All Hands

- **Geofry:** AI logic works, backend responds correctly
- **Person 2:** App is beautiful, easy to use, printable
- **Person 3:** Data is accurate, test cases are realistic
- **Person 4:** Everything is live, URLs work, no downtime

**Final message:** You're building something Kenya's clinics actually need. Do it right, help each other, and ship it.

**See you Sept 25!**
