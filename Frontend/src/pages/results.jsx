import { useEffect, useState } from "react";
import Head from "next/head";
import Link from "next/link";
import TriageResult from "../components/TriageResult";
import ReferralSlip from "../components/ReferralSlip";
import { normalizeTriageResult } from "../utils/formatOutput";

export default function ResultsPage() {
  const [stored, setStored] = useState(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("meditriage:lastResult");
    if (raw) setStored(JSON.parse(raw));
  }, []);

  if (!stored) {
    return (
      <div className="page">
        <Head>
          <title>Results — MediTriage AI</title>
        </Head>
        <h1>No result yet</h1>
        <p>Start a new assessment to see a triage result here.</p>
        <Link href="/intake" className="btn btn-primary">
          Start triage
        </Link>
      </div>
    );
  }

  const normalized = normalizeTriageResult(stored.result);

  return (
    <div className="page">
      <Head>
        <title>Triage result — MediTriage AI</title>
      </Head>

      <p className="eyebrow no-print">Step 2 of 2</p>
      <h1 className="no-print">Triage result</h1>

      <TriageResult result={normalized} />

      <ReferralSlip result={normalized} patient={stored.patient} />

      <Link href="/intake" className="btn btn-secondary btn-block no-print" style={{ marginTop: "12px" }}>
        Start a new assessment
      </Link>
    </div>
  );
}
