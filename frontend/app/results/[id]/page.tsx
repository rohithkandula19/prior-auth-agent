import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { AppealPanel } from "@/components/AppealPanel";
import { CitationCards } from "@/components/CitationCards";
import { CounterfactualPanel } from "@/components/CounterfactualPanel";
import { CriteriaChecklist, metCount } from "@/components/CriteriaChecklist";
import type { DecisionType } from "@/lib/types";

export const dynamic = "force-dynamic";

const DECISION_LABEL: Record<DecisionType, string> = {
  approved: "Approved",
  denied: "Denied",
  needs_more_info: "Needs more info",
};

const DECISION_BADGE: Record<DecisionType, string> = {
  approved: "bg-emerald-50/70 text-approved ring-emerald-100",
  denied: "bg-red-50/70 text-denied ring-red-100",
  needs_more_info: "bg-amber-50/70 text-pending ring-amber-100",
};

const DECISION_ICON: Record<DecisionType, React.ReactNode> = {
  approved: (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8l3 3 7-7" />
    </svg>
  ),
  denied: (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  ),
  needs_more_info: (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor">
      <circle cx="8" cy="8" r="2" />
    </svg>
  ),
};

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms} ms`;
}

export default async function ResultsPage({
  params,
}: {
  params: { id: string };
}) {
  let determination, policy, patient;
  try {
    determination = await api.getDetermination(params.id);
    [policy, patient] = await Promise.all([
      api.getPolicy(determination.policy_id),
      api.getPatient(determination.patient_id),
    ]);
  } catch {
    notFound();
  }

  const counts = metCount(determination.criterion_evaluations);
  const decision = determination.decision;
  const detIdShort = determination.id.toUpperCase().replace(/^DET_?/, "DET-");

  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-soft">
            <span className="eyebrow">{detIdShort}</span>
            <span className="text-rule">·</span>
            <span>{formatLatency(determination.latency_ms)}</span>
            <span className="text-rule">·</span>
            <span>${determination.cost_usd.toFixed(4)}</span>
          </div>
          <a
            href={`${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/determinations/${determination.id}/pdf`}
            className="rounded-md border border-rule bg-canvas px-3 py-1.5 text-xs hover:border-ink/40"
            target="_blank"
            rel="noopener"
          >
            Download PDF
          </a>
        </div>
        <h1 className="h-display text-[40px] tracking-tightest">
          {policy.procedure_name}{" "}
          <span className="text-rule">·</span>{" "}
          <span className="text-soft">{patient.id}</span>
        </h1>
      </header>

      <section className="surface px-8 py-7">
        <div className="flex flex-wrap items-baseline justify-between gap-6">
          <div className="flex items-center gap-4">
            <span
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ring-1 ring-inset ${DECISION_BADGE[decision]}`}
            >
              {DECISION_ICON[decision]}
              {DECISION_LABEL[decision]}
            </span>
            <span className="text-sm text-body">
              {counts.met} of {counts.total} criteria met
            </span>
          </div>
          <div className="text-right">
            <p className="eyebrow">Confidence</p>
            <p className="h-display text-[34px]">
              {determination.confidence.toFixed(2)}
            </p>
          </div>
        </div>
        <p className="mt-5 text-sm text-body">{determination.recommended_action}</p>
        {determination.gaps.length > 0 ? (
          <div className="mt-5 rounded-md bg-amber-50/70 px-4 py-3 text-sm text-pending">
            <p className="eyebrow mb-1 text-pending">Documentation gaps</p>
            <ul className="list-inside list-disc space-y-1 text-amber-900">
              {determination.gaps.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <CitationCards
        policy={policy}
        patient={patient}
        evaluations={determination.criterion_evaluations}
      />

      <section className="surface px-8 py-7">
        <p className="eyebrow mb-4">Criteria</p>
        <CriteriaChecklist
          policy={policy}
          patient={patient}
          evaluations={determination.criterion_evaluations}
        />
      </section>

      {decision !== "approved" ? <CounterfactualPanel determinationId={determination.id} /> : null}
      {decision !== "approved" ? <AppealPanel determinationId={determination.id} /> : null}
    </div>
  );
}
