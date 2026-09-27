// Client-side wrapper around the backend triage endpoint.
// This is NOT a Next.js API route (the backend is a separate FastAPI
// service on Render) — it just centralizes the call so pages don't
// import utils/api-client directly. Kept per the structure in
// TECHNICAL_ARCHITECTURE.md / AGENT.md.

export { runFullTriage as submitTriage } from "../../utils/api-client";
