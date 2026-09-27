import { useState } from "react";
import Head from "next/head";
import Link from "next/link";
import TriageResult from "../components/TriageResult";
import ReferralSlip from "../components/ReferralSlip";

// Hardcoded scenarios for the hackathon demo — used if the live backend is
// unreachable, or to walk judges through results without waiting on the API.
// All cost/coverage text uses SHA/SHIF, per SHA_UPDATE_CRITICAL.md.
const SCENARIOS = [
  {
    label: "Severe malaria (fever + confusion)",
    patient: { age: 34, symptoms: "High fever, confusion, and severe body aches for 2 days" },
    result: {
      triageLevel: "RED",
      urgency: "EMERGENCY",
      rationale: "High fever with confusion suggests possible severe/cerebral malaria — a life-threatening emergency.",
      instruction: "Go to the nearest hospital immediately. Tell them you have SHA coverage.",
      location: "Nearest Sub-County Hospital",
      cost: "Covered by SHA's Emergency, Chronic & Critical Illness Fund (ECCIF)",
      whatToBring: ["SHA registration or ID", "Any current medications"],
      dangerSigns: ["Worsening confusion", "Seizures", "Difficulty waking"],
    },
  },
  {
    label: "Hypertension follow-up",
    patient: { age: 58, symptoms: "Routine blood pressure check, feeling fine, on medication" },
    result: {
      triageLevel: "GREEN",
      urgency: "ROUTINE",
      rationale: "Stable, asymptomatic follow-up for a known chronic condition.",
      instruction: "No urgent visit needed. Continue your medication and monitor at home.",
      location: "Home",
      cost: "Free — no clinic visit needed",
      whatToBring: [],
      dangerSigns: ["Chest pain", "Severe headache", "Blurred vision"],
    },
  },
  {
    label: "Chest pain",
    patient: { age: 47, symptoms: "Chest pain and shortness of breath, started 1 hour ago" },
    result: {
      triageLevel: "RED",
      urgency: "EMERGENCY",
      rationale: "Chest pain with shortness of breath is treated as a possible cardiac emergency until ruled out.",
      instruction: "Go to hospital immediately. Do not drive yourself — call for transport.",
      location: "Nearest hospital with emergency care",
      cost: "Covered by SHA's Emergency, Chronic & Critical Illness Fund (ECCIF)",
      whatToBring: ["SHA registration or ID"],
      dangerSigns: ["Worsening pain", "Fainting", "Blue lips or fingertips"],
    },
  },
  {
    label: "Depression symptoms",
    patient: { age: 29, symptoms: "Low mood, low energy, and trouble sleeping for 3 weeks" },
    result: {
      triageLevel: "YELLOW",
      urgency: "URGENT",
      rationale: "Persistent low mood over several weeks warrants a same-day counselor visit.",
      instruction: "Come to the clinic today to speak with a counselor.",
      location: "This health center",
      cost: "Covered under SHA's Primary Healthcare Fund (mental health services included)",
      whatToBring: ["SHA registration or ID"],
      dangerSigns: ["Thoughts of self-harm", "Inability to care for yourself"],
    },
  },
  {
    label: "Cough / cold",
    patient: { age: 22, symptoms: "Mild cough and runny nose for 2 days, no fever" },
    result: {
      triageLevel: "GREEN",
      urgency: "ROUTINE",
      rationale: "Mild upper respiratory symptoms without fever or red flags.",
      instruction: "Manage at home: rest, fluids, and monitor for 3 days.",
      location: "Home",
      cost: "Free — no clinic visit needed",
      whatToBring: [],
      dangerSigns: ["Fever develops", "Difficulty breathing", "Symptoms worsen after 3 days"],
    },
  },
];

export default function DemoPage() {
  const [index, setIndex] = useState(0);
  const scenario = SCENARIOS[index];

  return (
    <div className="page">
      <Head>
        <title>Demo scenarios — MediTriage AI</title>
      </Head>

      <p className="eyebrow no-print">Offline demo mode</p>
      <h1 className="no-print">Sample triage scenarios</h1>
      <p className="no-print">
        Hardcoded test cases for the hackathon demo — use these if the live API is
        unreachable, or to walk through results quickly.
      </p>

      <div className="no-print" style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "20px" }}>
        {SCENARIOS.map((s, i) => (
          <button
            key={s.label}
            type="button"
            onClick={() => setIndex(i)}
            className="btn"
            style={{
              padding: "8px 14px",
              fontSize: "0.85rem",
              background: i === index ? "var(--color-clinic)" : "transparent",
              color: i === index ? "#fff" : "var(--color-ink)",
              border: "1px solid var(--color-line)",
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

      <TriageResult result={scenario.result} />
      <ReferralSlip result={scenario.result} patient={scenario.patient} />

      <Link href="/" className="btn btn-secondary btn-block no-print" style={{ marginTop: "12px" }}>
        Back home
      </Link>
    </div>
  );
}
