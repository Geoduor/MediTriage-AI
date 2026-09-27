# Data Sources

These sources back the clinical and cost content in `conditions.json`, `triage_rules.json`,
and `sha_benefits.json`. For the hackathon MVP this data is hand-curated from public guidance;
**Person 4's clinical validation checklist should confirm this against a real health worker
before it's presented as validated.**

## Disease Burden & Prevalence
- Kenya Ministry of Health, Kenya Health Information System (KHIS) outpatient morbidity reports
- WHO Country Health Profile - Kenya
- Kenya Malaria Indicator Survey (malaria remains a top-3 cause of outpatient visits nationally)

## SHA / Insurance Coverage
- SHA official site: https://sha.go.ke/
- SHA Act, 2023 (established SHA, SHIF, PHF, and ECCIF, replacing the NHIF Act)
- Ministry of Health public statements on SHA rollout (October 2024 - present)
- **See also:** `../../SHA_MAPPING.md` for the explicit NHIF → SHA field mapping used to
  update this data from its pre-October-2024 draft.

## Triage Guidelines
- WHO Emergency Triage Assessment and Treatment (ETAT) guidelines
- Kenya National Clinical Guidelines for primary care (general reference for red-flag symptoms)

## Symptoms & Differential Diagnosis
- WHO Integrated Management of Adolescent and Adult Illness (IMAI) guidelines
- CDC clinical reference for malaria, respiratory infection, and gastroenteritis presentation

## Known Limitations (be upfront with judges about these)
- Cost figures (e.g. "KES 0 at dispensary") reflect SHA's stated benefit structure, not a
  verified facility-level audit - some facilities had implementation gaps during the
  2024-2025 SHA transition.
- Swahili translations are conversational, not clinically reviewed by a native
  medical-Swahili speaker - flag for Person 4 to sanity-check with a health worker.
- This is a curated MVP dataset for a hackathon demo, not a substitute for a licensed
  clinician's judgment.
