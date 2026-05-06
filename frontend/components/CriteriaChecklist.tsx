import type { CriterionEvaluation, Policy } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";

const STATUS_TONE: Record<
  CriterionEvaluation["status"],
  "approved" | "denied" | "pending" | "neutral"
> = {
  met: "approved",
  not_met: "denied",
  partial: "pending",
  insufficient_evidence: "neutral",
};

const STATUS_LABEL: Record<CriterionEvaluation["status"], string> = {
  met: "Met",
  not_met: "Not met",
  partial: "Partial",
  insufficient_evidence: "Insufficient",
};

export function CriteriaChecklist({
  policy,
  evaluations,
}: {
  policy: Policy;
  evaluations: CriterionEvaluation[];
}) {
  const byId = new Map(policy.criteria.map((c) => [c.id, c]));
  return (
    <ol className="divide-y divide-line">
      {evaluations.map((ev) => {
        const crit = byId.get(ev.criterion_id);
        if (!crit) return null;
        return (
          <li key={ev.criterion_id} className="space-y-2 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-slate-500">{crit.id}</span>
                  <Badge tone={crit.type === "contraindication" ? "denied" : "info"}>
                    {crit.type}
                  </Badge>
                  <Badge tone={STATUS_TONE[ev.status]}>{STATUS_LABEL[ev.status]}</Badge>
                </div>
                <p className="text-sm text-slate-800">{crit.text}</p>
                {ev.reasoning ? (
                  <p className="text-xs text-slate-500">Reasoning: {ev.reasoning}</p>
                ) : null}
                {ev.supporting_evidence.length > 0 ? (
                  <p className="text-xs text-slate-500">
                    Supported by:{" "}
                    <span className="font-mono">{ev.supporting_evidence.join(", ")}</span>
                  </p>
                ) : null}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
