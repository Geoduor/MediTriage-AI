// Helpers for turning a /api/full-triage response into display-ready values.

export const TRIAGE_META = {
  RED: {
    className: "triage-red",
    label: "RED",
    plainLanguage: "Emergency — go now",
  },
  YELLOW: {
    className: "triage-yellow",
    label: "YELLOW",
    plainLanguage: "Urgent — go today",
  },
  GREEN: {
    className: "triage-green",
    label: "GREEN",
    plainLanguage: "Routine — can manage at home",
  },
};

/** Returns the CSS class + plain-language label for a triage level, with a safe fallback. */
export function getTriageMeta(triageLevel) {
  return (
    TRIAGE_META[triageLevel] || {
      className: "triage-yellow",
      label: triageLevel || "UNKNOWN",
      plainLanguage: "Please confirm with a health worker",
    }
  );
}

export function formatDate(date = new Date()) {
  return date.toLocaleDateString("en-KE", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Coerce any value into something React can safely render.
 *
 * The backend returns several fields as OBJECTS (`facility`, `cost`, `sha`).
 * Rendering one of those directly throws "Objects are not valid as a React
 * child" and blanks the page, so every displayed value goes through here.
 */
function asText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => asText(item)).filter(Boolean).join(", ");
  if (typeof value === "object") {
    return asText(
      value.name || value.statement || value.label || value.code,
      fallback
    );
  }
  return fallback;
}

/**
 * Normalizes a full-triage API response into flat fields the UI can render.
 *
 * Field names MUST match the FastAPI response in docs/API_DOCS.md:
 *   triage.triage_level / urgency / rationale / recommended_pathway / sha_fund
 *   care_pathway.patient_instruction / facility.name / cost.statement
 *                 / what_to_bring / danger_signs_to_watch / disclaimer
 */
export function normalizeTriageResult(result) {
  const triage = result?.triage || {};
  const pathway = result?.care_pathway || {};

  return {
    triageLevel: asText(triage.triage_level, "YELLOW"),
    urgency: asText(triage.urgency),
    rationale: asText(triage.rationale),
    recommendedPathway: asText(triage.recommended_pathway),
    matchedRule: asText(triage.matched_rule?.rule_id),
    shaFund: asText(pathway.sha?.fund_code || triage.sha_fund),

    // The pipeline returns `patient_instruction`. The older names are kept as
    // fallbacks so this adapter keeps working if the backend renames a field.
    instruction: asText(
      pathway.patient_instruction ||
        pathway.personalized_instruction ||
        pathway.instruction,
      "Please see a health worker for next steps."
    ),

    // `facility` is an object; the human-readable string is `facility.name`.
    location: asText(pathway.facility?.name || pathway.facility || pathway.location),

    // `cost` is an object; the sentence to show is `cost.statement`.
    cost: asText(
      pathway.cost?.statement || pathway.cost || pathway.estimated_cost
    ),

    whatToBring: (pathway.what_to_bring || []).map((item) => asText(item)).filter(Boolean),
    dangerSigns: (pathway.danger_signs_to_watch || pathway.danger_signs || [])
      .map((sign) => asText(sign))
      .filter(Boolean),
    followUp: asText(pathway.follow_up),
    disclaimer: asText(pathway.disclaimer),
  };
}
