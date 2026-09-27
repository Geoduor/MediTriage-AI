import { useState } from "react";

// Pre-defined quick-select symptoms. Kept short and specific to the
// 10 Kenyan conditions this MVP triages (see TECHNICAL_ARCHITECTURE.md).
const COMMON_SYMPTOMS = [
  "Fever",
  "Cough",
  "Headache",
  "Chest pain",
  "Difficulty breathing",
  "Diarrhea",
  "Vomiting",
  "Body aches",
  "Skin rash",
  "Low mood / anxiety",
];

function SymptomChecklist({ selected, onToggle }) {
  return (
    <div className="form-group">
      <label>Quick-select symptoms (optional)</label>
      <p className="form-hint">Tap any that apply — you can still describe things in your own words below.</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {COMMON_SYMPTOMS.map((symptom) => {
          const active = selected.includes(symptom);
          return (
            <button
              type="button"
              key={symptom}
              onClick={() => onToggle(symptom)}
              className="btn"
              style={{
                padding: "8px 14px",
                fontSize: "0.9rem",
                background: active ? "var(--color-clinic)" : "transparent",
                color: active ? "#fff" : "var(--color-ink)",
                border: "1px solid var(--color-line)",
              }}
              aria-pressed={active}
            >
              {symptom}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function FreeTextInput({ value, onChange }) {
  return (
    <div className="form-group">
      <label htmlFor="symptom-text">Describe symptoms in your own words</label>
      <textarea
        id="symptom-text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="E.g. 'I have had a high fever, headache, and body aches for 2 days.'"
        rows={5}
      />
    </div>
  );
}

function PatientContext({ context, onChange }) {
  return (
    <div className="form-group">
      <label>Patient context</label>
      <div className="checkbox-row">
        <input
          id="ctx-hiv"
          type="checkbox"
          checked={!!context.hiv_positive}
          onChange={(e) => onChange({ ...context, hiv_positive: e.target.checked })}
        />
        <label htmlFor="ctx-hiv">HIV-positive</label>
      </div>
      <div className="checkbox-row">
        <input
          id="ctx-pregnant"
          type="checkbox"
          checked={!!context.pregnant}
          onChange={(e) => onChange({ ...context, pregnant: e.target.checked })}
        />
        <label htmlFor="ctx-pregnant">Pregnant</label>
      </div>
      <div className="checkbox-row">
        <input
          id="ctx-chronic"
          type="checkbox"
          checked={!!context.has_chronic_condition}
          onChange={(e) =>
            onChange({ ...context, has_chronic_condition: e.target.checked })
          }
        />
        <label htmlFor="ctx-chronic">Has a chronic condition (diabetes, hypertension, etc.)</label>
      </div>
    </div>
  );
}

/**
 * Full patient intake form. Calls onSubmit with a payload shaped for
 * POST /api/full-triage (see AGENT.md for the exact contract).
 */
export default function IntakeForm({ onSubmit, loading }) {
  const [age, setAge] = useState("");
  const [symptomText, setSymptomText] = useState("");
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);
  const [context, setContext] = useState({});
  const [validationError, setValidationError] = useState("");

  function toggleSymptom(symptom) {
    setSelectedSymptoms((prev) =>
      prev.includes(symptom) ? prev.filter((s) => s !== symptom) : [...prev, symptom]
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    const combinedSymptoms = [selectedSymptoms.join(", "), symptomText.trim()]
      .filter(Boolean)
      .join(". ");

    if (!combinedSymptoms) {
      setValidationError("Please select at least one symptom or describe what's wrong.");
      return;
    }
    if (!age) {
      setValidationError("Please enter the patient's age.");
      return;
    }

    setValidationError("");
    onSubmit({
      symptoms: combinedSymptoms,
      patient_age: Number(age),
      patient_context: context,
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="patient-age">Age</label>
        <input
          id="patient-age"
          type="number"
          min="0"
          max="120"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          placeholder="e.g. 35"
        />
      </div>

      <SymptomChecklist selected={selectedSymptoms} onToggle={toggleSymptom} />
      <FreeTextInput value={symptomText} onChange={setSymptomText} />
      <PatientContext context={context} onChange={setContext} />

      {validationError && <div className="error-banner">{validationError}</div>}

      <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
        {loading ? "Analyzing…" : "Get triage decision"}
      </button>
    </form>
  );
}
