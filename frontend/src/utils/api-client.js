// Thin fetch wrapper around Geofry's FastAPI backend.
// Base URL comes from NEXT_PUBLIC_API_URL (see .env.local.example).

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function post(path, body) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (networkErr) {
    throw new ApiError(
      "Could not reach the server. Check your connection and try again.",
      0
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const errBody = await response.json();
      detail = errBody?.detail || detail;
    } catch (_) {
      // response had no JSON body — keep default message
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}

/**
 * Runs the full triage pipeline (all 3 agents chained on the backend).
 * @param {{symptoms: string, patient_age: number, patient_context: object, language?: string}} payload
 */
export function runFullTriage(payload) {
  return post("/api/full-triage", {
    language: "en",
    ...payload,
  });
}

/** Individual agent calls — only needed if the UI is split into steps. */
export function analyzeSymptoms(payload) {
  return post("/api/analyze-symptoms", payload);
}

export function getTriageDecision(payload) {
  return post("/api/triage-decision", payload);
}

export function getCarePathway(payload) {
  return post("/api/care-pathway", payload);
}

export { ApiError, API_URL };
