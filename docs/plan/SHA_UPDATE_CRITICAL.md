# CRITICAL UPDATE: SHA Replaces NHIF - MediTriage AI 2026

## What Changed (October 2024 - NOW)

<cite index="36-1">The SHA (Social Health Authority) replaced the previous National Health Insurance Fund (NHIF) through an Act of Parliament on 22 November 2023 and began operations on 1 October 2024.</cite>

**IMPORTANT:** All NHIF references in your project files have been updated to SHA/SHIF. Make sure your team understands this transition.

---

## SHA vs NHIF - Quick Breakdown

### OLD SYSTEM (NHIF - until October 2024)
- ❌ Graduated monthly premiums (KES 150 - KES 1,700 based on income)
- ❌ Limited coverage (gaps in many services)
- ❌ Complex, fragmented benefit packages
- ❌ Excluded many informal sector workers

### NEW SYSTEM (SHA/SHIF - October 2024 onwards)

<cite index="40-1">The Social Health Authority (SHA) replaced NHIF (National Hospital Insurance Fund) as Kenya's primary public health insurance system in 2024-2025. All Kenyans (with limited exceptions) contribute 2.75% of household monthly income, with a minimum contribution of KES 300/month. Coverage broadened - outpatient consultations, primary care visits, drugs, and many specialist services are covered without referral.</cite>

**Key Changes:**
- ✅ **Flat rate:** 2.75% of gross income (minimum KES 300/month)
- ✅ **Broader coverage:** Outpatient, inpatient, specialist care, maternity, mental health, chronic disease management
- ✅ **Three-fund structure:** 
  - Primary Healthcare Fund (PHF) - preventive services
  - Social Health Insurance Fund (SHIF) - core coverage
  - Emergency, Chronic and Critical Illness Fund (ECCIF) - catastrophic care
- ✅ **Mandatory for all:** All Kenyans 18+ must register
- ✅ **No referral needed:** Can access specialist services directly

---

## What This Means for MediTriage AI

### Updated Coverage Logic

**Your Care Pathway Agent now tells patients:**

```
OLD (NHIF):
"You'll be covered under NHIF (depending on which scheme you're in)"

NEW (SHA/SHIF):
"You'll be covered under SHA/SHIF - free at dispensary level for primary care, 
reduced cost for specialist services. Contribution: 2.75% of your income 
(minimum KES 300/month)"
```

### Three SHA Funds Your Triage Needs to Reference

**Primary Healthcare Fund (PHF)** ← Most relevant to your triage
- Covers: Preventive services, routine outpatient at dispensaries/health centers
- Cost to patient: FREE at dispensary level
- **Your triage sends here:** GREEN cases (routine, preventive)
- Example: "Malaria test and basic treatment at health center - covered"

**Social Health Insurance Fund (SHIF)** ← For urgent/specialist cases
- Covers: Inpatient admission, specialist care, surgery, maternity
- Cost to patient: Reduced cost (2.75% contribution covers this)
- **Your triage sends here:** YELLOW/RED cases (hospital referral)
- Example: "Admission to hospital for severe malaria - covered under SHIF"

**Emergency, Chronic and Critical Illness Fund (ECCIF)** ← For emergencies
- Covers: Major emergencies, catastrophic illness, cancer, organ transplants, dialysis
- Cost to patient: Fully covered
- **Your triage sends here:** RED emergencies (cardiac, severe trauma, advanced disease)
- Example: "Chest pain requiring ICU admission - covered by ECCIF"

---

## Updated Patient Cost Information

### What Patients Actually Pay (2026)

**At Dispensary/Health Center (PRIMARY HEALTHCARE):**
- **Routine visit:** KES 0 (free - covered by SHA)
- **Malaria test:** Free
- **Common antibiotics:** Free/subsidized
- Patient only pays: Transportation to clinic

**At Hospital (for referral cases):**
- **Inpatient stay:** Covered by SHIF (patient pays 2.75% contribution)
- **Specialist consultation:** Covered or minimal co-pay
- Patient may pay: Small registration fee + medicine co-pays

**Major emergencies:**
- **ICU admission, surgery, emergency care:** Covered by ECCIF
- Patient pays: Minimal to nothing (catastrophic coverage)

---

## Updated Triage Rules for SHA

### Care Pathway Recommendations (2026)

**RED Cases (Emergency) → Hospital/ECCIF**
```
"This is an emergency. Go to the nearest hospital IMMEDIATELY.
Your SHA/SHIF will cover emergency and critical care.
Tell them you have SHA coverage."
```

**YELLOW Cases (Urgent) → Today at clinic/Health center (SHIF)**
```
"Come to the health center/clinic TODAY.
Your malaria test and treatment are FREE under SHA's Primary Healthcare Fund.
Bring your SHA registration or ID."
```

**GREEN Cases (Routine) → Home or routine clinic (PHF)**
```
"You can manage this at home. If symptoms worsen after 3 days, visit a clinic.
Routine care at dispensary/health center is FREE under SHA.
No need to visit a hospital."
```

---

## Important SHA Facts for Your Team

### 1. SHA Transition Was Rough (Oct 2024 - Apr 2025)
<cite index="40-1">The transition was rocky, system bugs, member-data migration issues, and confusion about contribution rates characterised the first year.</cite>

**What this means for your triage:** Patients may be confused about SHA coverage. Your system should clearly explain what's covered.

### 2. SHA is Mandatory Now (2026)
<cite index="40-1">Mandatory enrollment. All Kenyans aged 18+ must register, regardless of employment status.</cite>

**What this means for your triage:** Almost all patients at clinics should have SHA coverage (no more "uninsured" patients).

### 3. Fraud Concerns Exist
<cite index="42-1">In January 2026, a Ministry of Health audit revealed SHA lost approximately KES 11 billion to fraud between October 2024 and April 2025, mostly from fake claims by private hospitals.</cite>

**What this means for your triage:** Your system should be aware that SHA/Ministry are cracking down on unnecessary referrals to expensive private hospitals. Accurate triage helps SHA save money and catches fraudulent referrals.

### 4. Coverage is NOW Much Broader
<cite index="42-1">SHIF (the core contributory scheme replacing NHIF) covers outpatient consultations, inpatient admissions, surgeries, maternity care, chronic disease management, mental health services, and rehabilitation.</cite>

**What this means for your triage:** Patients can access specialist/mental health services without referral now. Your triage can direct patients directly to specialists in some cases.

---

## Updated Files (What Changed)

All project files have been updated:

| File | What Changed |
|------|-------------|
| `TEAM_BRIEF.md` | NHIF → SHA/SHIF |
| `TECHNICAL_ARCHITECTURE.md` | NHIF → SHA/SHIF |
| `TEAM_TASK_BREAKDOWN.md` | NHIF → SHA/SHIF |
| `PROJECT_OVERVIEW.md` | NHIF → SHA/SHIF |
| `STRUCTURE_VISUAL.txt` | NHIF → SHA/SHIF |
| `TOOL_ANALYSIS.md` | NHIF → SHA/SHIF |
| `CORRECTIONS_SUMMARY.md` | NHIF → SHA/SHIF |

---

## Action Items for Your Team

### Before Hackathon (Sept 25-27)
```
✓ Read this document
✓ Understand: SHA replaced NHIF in October 2024
✓ Update test cases: Use SHA coverage, not old NHIF bands
✓ Update dummy data: 
  - Old: "NHIF: KES 150-1700/month"
  - New: "SHA/SHIF: 2.75% income, minimum KES 300/month"
```

### Test Cases to Update

**OLD Test Case (NHIF):**
```
Patient: 35-year-old, malaria suspected
Cost info: "NHIF covers this" (which scheme? Confusion!)
```

**NEW Test Case (SHA/SHIF):**
```
Patient: 35-year-old, malaria suspected, has SHA coverage
Cost info: "PRIMARY HEALTHCARE FUND covers malaria test and treatment at dispensary. FREE."
Next triage level: YELLOW (urgent clinic visit today)
Expected patient cost: KES 0 at clinic + transport
```

### Data Files to Update

**conditions.json:**
```json
{
  "id": 1,
  "name": "Malaria",
  "treatment_location": "clinic or hospital (if severe)",
  "estimated_cost": "0 KES at dispensary (covered by SHA Primary Healthcare Fund)",
  "sha_covered": true,
  "sha_fund": "Primary Healthcare Fund (PHF) for routine, SHIF for severe"
}
```

**nhif_benefits.json → sha_benefits.json:**
```json
{
  "facility_level": "dispensary",
  "services": ["Malaria test", "Basic consultation", "Common antibiotics"],
  "sha_fund": "Primary Healthcare Fund (PHF)",
  "patient_cost": "KES 0 (FREE)",
  "sha_covers": true
}
```

---

## Reference Links

- **SHA Official Site:** https://sha.go.ke/
- **SHA Paybill (for contributions):** 200222
- **Ministry of Health:** Kenya MoH official documentation

---

## Key Takeaway

**SHA is BETTER for MediTriage:**
- ✅ More people covered (mandatory)
- ✅ Clearer cost structure (2.75% flat rate)
- ✅ Broader services covered
- ✅ Your triage helps SHA by preventing unnecessary referrals (they're cracking down on fraud)

**Make sure:**
- All test data uses SHA (not old NHIF)
- Care Pathway Agent explains SHA coverage clearly
- Cost info is accurate for 2026 (KES 300 minimum, 2.75% rate)

---

## Questions?

If your team has questions about SHA:
1. Check sha.go.ke
2. Ask a health worker at your pilot clinic
3. Reference this document

**One more thing:** Since this is a REAL system facing REAL patients in 2026, getting SHA right is critical. This isn't just terminology - it affects what you tell patients about cost and coverage.

---

**Updated:** September 25, 2026  
**Relevance:** CRITICAL - All hackathon test cases should use SHA, not NHIF
