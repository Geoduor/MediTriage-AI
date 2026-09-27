import { getTriageMeta, formatDate } from "../utils/formatOutput";

function Header({ date }) {
  return (
    <div className="slip-header">
      <div>
        <strong>MediTriage AI</strong>
        <div style={{ fontSize: "0.85rem", color: "var(--color-ink-soft)" }}>
          Clinic Referral Slip
        </div>
      </div>
      <div style={{ fontSize: "0.9rem" }}>{date}</div>
    </div>
  );
}

function PatientInfo({ age, symptoms }) {
  return (
    <div className="slip-row">
      <div>
        <strong>Age:</strong> {age || "—"}
      </div>
      <div>
        <strong>Reported symptoms:</strong> {symptoms || "—"}
      </div>
    </div>
  );
}

function TriageDecision({ result }) {
  const meta = getTriageMeta(result.triageLevel);
  return (
    <div className="slip-row">
      <strong>Triage level: </strong>
      <span
        className="triage-badge"
        style={{ background: `var(--color-${meta.className.replace("triage-", "")})`, color: "#111" }}
      >
        {meta.label}
      </span>
      <p style={{ marginTop: "6px" }}>{result.rationale}</p>
    </div>
  );
}

function CareInstructions({ result }) {
  return (
    <div className="slip-row">
      <strong>Instructions:</strong>
      <p>{result.instruction}</p>
      {result.location && (
        <p>
          <strong>Where to go:</strong> {result.location}
        </p>
      )}
      {result.cost && (
        <p>
          <strong>Expected cost:</strong> {result.cost}
        </p>
      )}
      {result.dangerSigns?.length > 0 && (
        <>
          <strong>Seek help immediately if you notice:</strong>
          <ul>
            {result.dangerSigns.map((sign) => (
              <li key={sign}>{sign}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

/**
 * Printable referral slip. `result` is the normalized triage result;
 * `patient` is { age, symptoms }.
 */
export default function ReferralSlip({ result, patient }) {
  return (
    <>
      <div className="referral-slip">
        <Header date={formatDate()} />
        <PatientInfo age={patient?.age} symptoms={patient?.symptoms} />
        <TriageDecision result={result} />
        <CareInstructions result={result} />
      </div>

      <button onClick={() => window.print()} className="btn btn-secondary btn-block no-print">
        Print referral slip
      </button>
    </>
  );
}
