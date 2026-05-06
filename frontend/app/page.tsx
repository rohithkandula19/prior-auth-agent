import Link from "next/link";

export default function Page() {
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <p className="text-xs uppercase tracking-widest text-slate-500">
          Prior authorization, explained
        </p>
        <h1 className="text-4xl font-semibold tracking-tight">
          Citation-grounded prior auth decisions
        </h1>
        <p className="max-w-2xl text-slate-600">
          Upload a payer policy and a patient chart. The agent checks each
          criterion, cites the exact spans of policy and chart that support
          its call, and returns a calibrated confidence score together with
          the gaps that block approval.
        </p>
        <div className="flex gap-3">
          <Link
            href="/determine"
            className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Run a determination
          </Link>
          <Link
            href="/policies"
            className="rounded-md border border-line bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
          >
            Browse policies
          </Link>
          <Link
            href="/eval"
            className="rounded-md border border-line bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
          >
            Eval dashboard
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          {
            title: "Verbatim citations",
            body: "Every criterion is cited back to a char span in the policy PDF and the chart. No paraphrase, no hallucinated text.",
          },
          {
            title: "Calibrated confidence",
            body: "Per-criterion certainty is aggregated into a decision-level probability and reviewed against a labeled gold set.",
          },
          {
            title: "Auditable trace",
            body: "Each criterion check is logged with the model output, supporting evidence, and reasoning so reviewers can spot-check fast.",
          },
        ].map((card) => (
          <div key={card.title} className="rounded-lg border border-line bg-white p-5">
            <h3 className="mb-2 text-sm font-semibold">{card.title}</h3>
            <p className="text-sm text-slate-600">{card.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
