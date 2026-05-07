"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { EvalSummary } from "@/lib/types";
import { CalibrationCurve } from "@/components/CalibrationCurve";
import { ModelCompare } from "@/components/ModelCompare";

const FAILURE_LABEL: Record<string, string> = {
  hallucinated_criterion: "Hallucinated criterion",
  missed_criterion: "Missed criterion",
  wrong_span_citation: "Wrong span citation",
  evidence_misread: "Evidence misread",
  logical_error: "Logical error",
  calibration_failure: "Calibration failure",
  latency_outlier: "Latency outlier",
  pipeline_error: "Pipeline error",
};

const DECISION_LABEL: Record<string, string> = {
  approved: "Approved",
  denied: "Denied",
  needs_more_info: "Needs more info",
};

function failureRows(
  fm: EvalSummary["failure_modes"]
): { key: string; count: number; pct: number }[] {
  if (!fm) return [];
  const entries = Object.entries(fm);
  const total = entries.reduce((s, [, v]) => s + (typeof v === "number" ? v : v.count), 0) || 1;
  return entries
    .map(([k, v]) => {
      const count = typeof v === "number" ? v : v.count;
      const pct = typeof v === "number" ? count / total : v.pct;
      return { key: k, count, pct };
    })
    .sort((a, b) => b.count - a.count);
}

function fmt(v: number | null | undefined): string {
  if (v === null || v === undefined) return "n/a";
  return v.toFixed(2);
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)} ms`;
}

export function EvalDashboard({ initial }: { initial: EvalSummary }) {
  const router = useRouter();
  const [summary, setSummary] = useState<EvalSummary>(initial);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setErr(null);
    try {
      const result = await api.runEval();
      setSummary(result.summary);
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const cases = summary.n;
  const agreement = summary.agreement ?? 0;
  const ece = summary.ece ?? 0;
  const p95 = summary.latency_ms?.p95 ?? 0;
  const p50 = summary.latency_ms?.p50 ?? 0;
  const cost = summary.avg_cost_usd ?? 0;
  const fm = failureRows(summary.failure_modes);
  const fmMax = Math.max(1, ...fm.map((r) => r.count));
  const decisions = summary.by_decision ?? {};
  const decisionEntries = Object.entries(decisions);

  return (
    <div className="space-y-16">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="space-y-3">
          <p className="eyebrow">Eval run {summary.run_version ?? "v1"}</p>
          <h1 className="h-display text-[44px] tracking-tightest">
            {cases} cases against gold standard.
          </h1>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-white disabled:opacity-30"
        >
          {running ? "Running..." : "Run eval"}
        </button>
      </div>
      {err ? <p className="text-xs text-red-700">{err}</p> : null}

      {/* Big numbers row */}
      <section className="grid gap-12 border-y border-rule py-8 md:grid-cols-4">
        <Stat label="Agreement" value={`${Math.round(agreement * 100)}%`} hint={agreement >= 0.8 ? "Above target" : "Below target"} hintTone={agreement >= 0.8 ? "good" : "warn"} />
        <Stat label="ECE" value={ece.toFixed(2)} hint={ece <= 0.1 ? "Well calibrated" : "Drift detected"} hintTone={ece <= 0.1 ? "good" : "warn"} />
        <Stat label="Latency p95" value={formatMs(p95)} hint={`p50 ${formatMs(p50)}`} />
        <Stat label="Cost" value={`$${cost.toFixed(2)}`} hint="per determination" />
      </section>

      {summary.citations && summary.citations.scored_cases > 0 ? (
        <section className="space-y-5">
          <div className="flex items-baseline justify-between">
            <p className="eyebrow">Citation precision and recall</p>
            <p className="text-xs text-soft">
              {summary.citations.scored_cases} scored case
              {summary.citations.scored_cases === 1 ? "" : "s"} · IoU 0.5
            </p>
          </div>
          <div className="grid gap-12 border-y border-rule py-7 md:grid-cols-3">
            <Stat label="Precision" value={fmt(summary.citations.precision)} />
            <Stat label="Recall" value={fmt(summary.citations.recall)} />
            <Stat label="F1" value={fmt(summary.citations.f1)} />
          </div>
        </section>
      ) : null}

      <div className="grid gap-12 md:grid-cols-2">
        <section className="space-y-5">
          <p className="eyebrow">Calibration curve</p>
          {summary.reliability && summary.reliability.length > 0 ? (
            <CalibrationCurve reliability={summary.reliability} />
          ) : (
            <p className="text-sm text-soft">No data yet.</p>
          )}
        </section>

        <section className="space-y-5">
          <p className="eyebrow">Decision class</p>
          {decisionEntries.length === 0 ? (
            <p className="text-sm text-soft">No data yet.</p>
          ) : (
            <ul className="space-y-6">
              {decisionEntries.map(([d, v]) => (
                <li key={d}>
                  <div className="mb-2 flex items-baseline justify-between">
                    <span className="text-[15px] text-ink">
                      {DECISION_LABEL[d] ?? d}
                    </span>
                    <span className="font-mono text-xs text-soft">
                      {v.correct} / {v.n}
                    </span>
                  </div>
                  <div className="h-1 w-full overflow-hidden rounded-full bg-rule">
                    <div
                      className="h-full rounded-full bg-ink"
                      style={{ width: `${(v.correct / Math.max(v.n, 1)) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <ModelCompare />

      <section className="space-y-5">
        <p className="eyebrow">Failure modes</p>
        {fm.length === 0 ? (
          <p className="text-sm text-soft">No failures detected.</p>
        ) : (
          <ul className="divide-y divide-rule">
            {fm.map((row) => (
              <li
                key={row.key}
                className="flex items-baseline justify-between gap-6 py-4"
              >
                <span className="text-[15px] text-ink">
                  {FAILURE_LABEL[row.key] ?? row.key.replace(/_/g, " ")}
                </span>
                <div className="flex items-center gap-5">
                  <div className="hidden h-1 w-48 rounded-full bg-rule sm:block">
                    <div
                      className="h-full rounded-full bg-ink/80"
                      style={{ width: `${(row.count / fmMax) * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-soft">
                    {row.count} {row.count === 1 ? "case" : "cases"} · {Math.round(row.pct * 100)}%
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  hintTone,
}: {
  label: string;
  value: string;
  hint?: string;
  hintTone?: "good" | "warn";
}) {
  const hintCls =
    hintTone === "good" ? "text-approved" : hintTone === "warn" ? "text-pending" : "text-soft";
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className="mt-3 h-display text-[44px] tracking-tightest">{value}</p>
      {hint ? <p className={`mt-1 text-xs ${hintCls}`}>{hint}</p> : null}
    </div>
  );
}
