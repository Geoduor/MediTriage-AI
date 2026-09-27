import { getTriageMeta } from "../utils/formatOutput";

function RedAlert({ meta, rationale, urgency }) {
  return (
    <div className={`triage-tag ${meta.className}`}>
      <div className="triage-level">{meta.label}</div>
      <div className="triage-urgency">{urgency || meta.plainLanguage}</div>
      <p className="triage-rationale">{rationale}</p>
    </div>
  );
}

function YellowWarning({ meta, rationale, urgency }) {
  return (
    <div className={`triage-tag ${meta.className}`}>
      <div className="triage-level">{meta.label}</div>
      <div className="triage-urgency">{urgency || meta.plainLanguage}</div>
      <p className="triage-rationale">{rationale}</p>
    </div>
  );
}

function GreenOK({ meta, rationale, urgency }) {
  return (
    <div className={`triage-tag ${meta.className}`}>
      <div className="triage-level">{meta.label}</div>
      <div className="triage-urgency">{urgency || meta.plainLanguage}</div>
      <p className="triage-rationale">{rationale}</p>
    </div>
  );
}

const LEVEL_COMPONENTS = {
  RED: RedAlert,
  YELLOW: YellowWarning,
  GREEN: GreenOK,
};

/**
 * Color-coded triage result. `result` is the normalized shape from
 * utils/formatOutput.js (normalizeTriageResult).
 */
export default function TriageResult({ result }) {
  const meta = getTriageMeta(result.triageLevel);
  const LevelComponent = LEVEL_COMPONENTS[result.triageLevel] || YellowWarning;

  return (
    <div>
      <LevelComponent meta={meta} rationale={result.rationale} urgency={result.urgency} />

      <div className="pathway-card">
        <h3>What to do</h3>
        <p style={{ color: "var(--color-ink)" }}>{result.instruction}</p>
        {result.location && (
          <p style={{ color: "var(--color-ink)", margin: 0 }}>
            <strong>Where:</strong> {result.location}
          </p>
        )}
        {result.cost && (
          <p style={{ color: "var(--color-ink)", margin: 0 }}>
            <strong>Cost:</strong> {result.cost}
          </p>
        )}
        {result.whatToBring?.length > 0 && (
          <>
            <strong>Bring with you:</strong>
            <ul>
              {result.whatToBring.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
