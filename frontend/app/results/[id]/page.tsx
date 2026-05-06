import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { CitationCards } from "@/components/CitationCards";
import { CriteriaChecklist, metCount } from "@/components/CriteriaChecklist";
import type { DecisionType } from "@/lib/types";

export const dynamic = "force-dynamic";

const DECISION_LABEL: Record<DecisionType, string> = {
  approved: "Approved",
  denied: "Denied",
  needs_more_info: "Needs more info",
};

const DECISION_BADGE: Record<DecisionType, string> = {
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  denied: "bg-red-50 text-red-700 ring-red-100",
  needs_more_info: "bg-amber-50 text-amber-700 ring-amber-100",
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
    <div className="space-y-10">
      <header className="space-y-3">
        <div className="flex items-center gap-2 text-xs">
          <span className="eyebrow">{detIdShort}</span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-500">{determination.latency_ms} ms</span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-500">${determination.cost_usd.toFixed(4)}</span>
        </div>
        <h1 className="text-[34px] font-semibold tracking-tight">
          {policy.procedure_name} <span className="text-slate-400">·</span> {patient.id}
        </h1>
      </header>

      <section className="rounded-xl border border-line/70 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <span
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ring-1 ring-inset ${DECISION_BADGE[decision]}`}
            >
              {DECISION_ICON[decision]}
              {DECISION_LABEL[decision]}
            </span>
            <span className="text-sm text-slate-500">
              {counts.met} of {counts.total} criteria met
            </span>
          </div>
          <div className="text-right">
            <p className="eyebrow">Confidence</p>
            <p className="text-3xl font-semibold tracking-tight">
              {determination.confidence.toFixed(2)}
            </p>
          </div>
        </div>
        {determination.gaps.length > 0 ? (
          <div className="mt-5 rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider">
              Documentation gaps
            </p>
            <ul className="list-inside list-disc space-y-0.5">
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

      <section className="rounded-xl border border-line/70 bg-white p-6">
        <p className="eyebrow mb-2">Criteria</p>
        <CriteriaChecklist
          policy={policy}
          patient={patient}
          evaluations={determination.criterion_evaluations}
        />
      </section>
    </div>
  );
}
