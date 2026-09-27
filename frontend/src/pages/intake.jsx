import { useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import IntakeForm from "../components/IntakeForm";
import { runFullTriage, ApiError } from "../utils/api-client";

export default function IntakePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(payload) {
    setLoading(true);
    setError("");
    try {
      const result = await runFullTriage(payload);
      // Stash the result + the patient-facing fields the slip needs.
      sessionStorage.setItem(
        "meditriage:lastResult",
        JSON.stringify({
          result,
          patient: { age: payload.patient_age, symptoms: payload.symptoms },
        })
      );
      router.push("/results");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <Head>
        <title>Patient assessment — MediTriage AI</title>
      </Head>

      <p className="eyebrow">Step 1 of 2</p>
      <h1>Patient assessment</h1>
      <p>Fill this in as the patient would describe it — their own words are fine.</p>

      {error && <div className="error-banner">{error}</div>}
      {loading && (
        <div className="spinner-row">
          <div className="spinner" aria-hidden="true" />
          <span>Analyzing symptoms…</span>
        </div>
      )}

      <IntakeForm onSubmit={handleSubmit} loading={loading} />
    </div>
  );
}
