import Link from "next/link";

export default function Page() {
  return (
    <div className="space-y-20">
      <section className="space-y-6">
        <p className="eyebrow">Prior authorization, audited</p>
        <h1 className="h-display max-w-3xl text-[56px] tracking-tightest text-ink">
          Decisions you can defend, citation by citation.
        </h1>
        <p className="max-w-xl text-[17px] leading-relaxed text-body">
          Upload a payer policy and a patient chart. The agent checks each
          criterion, cites the exact spans of policy and chart that support
          its call, and returns a calibrated confidence score with the gaps
          that block approval.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/determine"
            className="rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-white hover:bg-black"
          >
            Run a determination
          </Link>
          <Link
            href="/policies"
            className="rounded-md border border-rule bg-canvas px-4 py-2.5 text-sm font-medium text-ink hover:border-ink/40"
          >
            Browse policies
          </Link>
          <Link
            href="/eval"
            className="rounded-md border border-rule bg-canvas px-4 py-2.5 text-sm font-medium text-ink hover:border-ink/40"
          >
            Eval dashboard
          </Link>
        </div>
      </section>

      <section className="space-y-6">
        <p className="eyebrow">How it works</p>
        <div className="grid gap-x-12 gap-y-10 md:grid-cols-3">
          {[
            {
              n: "01",
              title: "Verbatim citations",
              body: "Every criterion is cited back to a char span in the policy PDF and the chart. No paraphrase, no hallucinated text.",
            },
            {
              n: "02",
              title: "Calibrated confidence",
              body: "Per-criterion certainty is aggregated into a decision-level probability, scored against a labelled gold set.",
            },
            {
              n: "03",
              title: "Auditable trace",
              body: "Each criterion check records the model output, supporting evidence, and reasoning so reviewers can spot-check fast.",
            },
          ].map((card) => (
            <div key={card.n} className="space-y-2">
              <p className="font-mono text-xs text-soft">{card.n}</p>
              <h3 className="text-[17px] font-medium text-ink">{card.title}</h3>
              <p className="text-[15px] leading-relaxed text-body">{card.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
