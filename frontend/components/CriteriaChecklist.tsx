import type { CriterionEvaluation, Patient, Policy } from "@/lib/types";

const STATUS_LABEL: Record<CriterionEvaluation["status"], string> = {
  met: "Met",
  not_met: "Not met",
  partial: "Partial",
  insufficient_evidence: "Insufficient",
};

function shortTitle(text: string, maxWords = 8): string {
  // First sentence or clause, truncated to a few words
  const cleaned = text.replace(/\s+/g, " ").trim();
  const firstSentence = cleaned.split(/(?<=[.;:])\s/)[0] ?? cleaned;
  const words = firstSentence.split(" ").slice(0, maxWords);
  return words.join(" ").replace(/[.,;:]+$/, "");
}

function detail(
  ev: CriterionEvaluation,
  patient: Patient
): string {
  if (ev.reasoning) return ev.reasoning.replace(/\s+/g, " ").trim();
  const byId = new Map(patient.evidence.map((e) => [e.id, e]));
  const ids = ev.supporting_evidence
    .map((id) => byId.get(id)?.description)
    .filter(Boolean) as string[];
  return ids.join(", ") || "Awaiting documentation";
}

function statusIcon(status: CriterionEvaluation["status"]) {
  if (status === "met") {
    return (
      <span className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-emerald-500 text-white">
        <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 8l3 3 7-7" />
        </svg>
      </span>
    );
  }
  if (status === "not_met") {
    return (
      <span className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-red-500 text-white">
        <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      </span>
    );
  }
  if (status === "partial") {
    return <span className="mt-0.5 inline-flex h-5 w-5 flex-none rounded-full bg-amber-400" />;
  }
  return (
    <span className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-slate-300 text-[10px] text-slate-500">
      ?
    </span>
  );
}

export function CriteriaChecklist({
  policy,
  patient,
  evaluations,
}: {
  policy: Policy;
  patient: Patient;
  evaluations: CriterionEvaluation[];
}) {
  const byId = new Map(policy.criteria.map((c) => [c.id, c]));
  return (
    <ul className="divide-y divide-line/70">
      {evaluations.map((ev) => {
        const crit = byId.get(ev.criterion_id);
        if (!crit) return null;
        return (
          <li key={ev.criterion_id} className="flex gap-3 py-4">
            {statusIcon(ev.status)}
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-semibold tracking-tight">
                {shortTitle(crit.text)}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                <span className="text-slate-700">{STATUS_LABEL[ev.status]}</span>
                <span className="mx-1.5 text-slate-300">·</span>
                {detail(ev, patient)}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function metCount(evaluations: CriterionEvaluation[]): { met: number; total: number } {
  return {
    met: evaluations.filter((e) => e.status === "met").length,
    total: evaluations.length,
  };
}
