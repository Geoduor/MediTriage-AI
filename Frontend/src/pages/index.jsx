import Head from "next/head";
import Link from "next/link";

export default function Home() {
  return (
    <div className="page">
      <Head>
        <title>MediTriage AI</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta
          name="description"
          content="Smart healthcare triage for Kenya's clinics — know where to go in 30 seconds."
        />
      </Head>

      <p className="eyebrow">Kenya · Primary care triage</p>
      <h1>MediTriage AI</h1>
      <p>
        Describe your symptoms and get a clear answer: go to hospital now, come to
        the clinic today, or manage this safely at home — with SHA coverage info
        included.
      </p>

      <div className="card">
        <h2>How it works</h2>
        <ol className="steps">
          <li>Describe your symptoms</li>
          <li>Our AI checks urgency — RED, YELLOW, or GREEN</li>
          <li>Get clear instructions on where to go and what it costs</li>
          <li>Print a referral slip to bring with you</li>
        </ol>
        <Link href="/intake" className="btn btn-primary btn-block">
          Start triage
        </Link>
      </div>

      <p style={{ fontSize: "0.85rem" }}>
        Not sure what to expect? <Link href="/demo">See a sample result</Link>.
      </p>
    </div>
  );
}
