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

/** Normalizes a full-triage API response into flat fields the UI can render directly. */
export function normalizeTriageResult(result) {
  const triage = result?.triage || {};
  const pathway = result?.care_pathway || {};

  return {
    triageLevel: triage.triage_level,
    urgency: triage.urgency,
    rationale: triage.rationale,
    recommendedPathway: triage.recommended_pathway,
    instruction:
      pathway.personalized_instruction ||
      pathway.instruction ||
      "Please see a health worker for next steps.",
    location: pathway.location || pathway.facility,
    cost: pathway.cost || pathway.estimated_cost,
    whatToBring: pathway.what_to_bring || [],
    dangerSigns: pathway.danger_signs || pathway.danger_signs_to_watch || [],
  };
}
