import type { DecisionType } from "@/lib/types";

const COLOR: Record<DecisionType, string> = {
  approved: "bg-emerald-500",
  denied: "bg-red-500",
  needs_more_info: "bg-amber-500",
};

const LABEL: Record<DecisionType, string> = {
  approved: "Approved",
  denied: "Denied",
  needs_more_info: "Needs more info",
};

export function ConfidenceMeter({
  decision,
  confidence,
}: {
  decision: DecisionType;
  confidence: number;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, confidence)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold">{LABEL[decision]}</span>
        <span className="font-mono text-xs text-slate-500">
          {pct}% confidence
        </span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`${COLOR[decision]} h-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
