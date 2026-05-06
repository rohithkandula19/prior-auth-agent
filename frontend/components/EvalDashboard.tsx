"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { EvalSummary } from "@/lib/types";
import { CalibrationCurve } from "@/components/CalibrationCurve";

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
    <div className="space-y-10">
      <div className="flex items-start justify-between gap-6">
        <div className="space-y-2">
          <p className="eyebrow">Eval run {summary.run_version ?? "v1"}</p>
          <h1 className="text-4xl font-semibold tracking-tight">
            {cases} cases against gold standard
          </h1>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {running ? "Running..." : "Run eval"}
        </button>
      </div>
      {err ? <p className="text-xs text-red-600">{err}</p> : null}

      <div className="grid gap-4 md:grid-cols-4">
        <Tile label="Agreement" value={`${Math.round(agreement * 100)}%`} hint={agreement >= 0.8 ? "Above target" : "Below target"} hintTone={agreement >= 0.8 ? "good" : "warn"} />
        <Tile label="ECE" value={ece.toFixed(2)} hint={ece <= 0.1 ? "Well calibrated" : "Drift detected"} hintTone={ece <= 0.1 ? "good" : "warn"} />
        <Tile label="Latency p95" value={`${formatMs(p95)}`} hint={`p50 ${formatMs(p50)}`} />
        <Tile label="Cost" value={`$${cost.toFixed(2)}`} hint="per determination" />
      </div>

      {summary.citations && summary.citations.scored_cases > 0 ? (
        <section className="rounded-xl border border-line/70 bg-white p-6">
          <p className="eyebrow mb-4">
            Citation precision and recall · {summary.citations.scored_cases} scored case
            {summary.citations.scored_cases === 1 ? "" : "s"}
          </p>
          <div className="grid gap-4 md:grid-cols-3">
            <Tile label="Precision" value={fmt(summary.citations.precision)} compact />
            <Tile label="Recall" value={fmt(summary.citations.recall)} compact />
            <Tile label="F1" value={fmt(summary.citations.f1)} compact />
          </div>
          <p className="mt-3 text-xs text-slate-500">
            IoU threshold 0.5. Spans are computed against verbatim chart
            substrings declared in the gold set.
          </p>
        </section>
      ) : null}

      <div className="grid gap-5 md:grid-cols-2">
        <section className="rounded-xl border border-line/70 bg-white p-6">
          <p className="eyebrow mb-4">Calibration curve</p>
          {summary.reliability && summary.reliability.length > 0 ? (
            <CalibrationCurve reliability={summary.reliability} />
          ) : (
            <p className="text-sm text-slate-500">No data yet.</p>
          )}
        </section>

        <section className="rounded-xl border border-line/70 bg-white p-6">
          <p className="eyebrow mb-4">Decision class</p>
          {decisionEntries.length === 0 ? (
            <p className="text-sm text-slate-500">No data yet.</p>
          ) : (
            <ul className="space-y-5">
              {decisionEntries.map(([d, v]) => (
                <li key={d}>
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="text-sm">{DECISION_LABEL[d] ?? d}</span>
                    <span className="font-mono text-xs text-slate-500">
                      {v.correct} / {v.n}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-100">
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

      <section className="rounded-xl border border-line/70 bg-white p-6">
        <p className="eyebrow mb-4">Failure modes</p>
        {fm.length === 0 ? (
          <p className="text-sm text-slate-500">No failures detected.</p>
        ) : (
          <ul className="divide-y divide-line/70">
            {fm.map((row) => (
              <li
                key={row.key}
                className="flex items-center justify-between gap-6 py-3"
              >
                <span className="text-sm font-medium">
                  {FAILURE_LABEL[row.key] ?? row.key.replace(/_/g, " ")}
                </span>
                <div className="flex items-center gap-4">
                  <div className="hidden h-1 w-40 rounded-full bg-slate-100 sm:block">
                    <div
                      className="h-full rounded-full bg-ink/70"
                      style={{ width: `${(row.count / fmMax) * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-slate-500">
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

function Tile({
  label,
  value,
  hint,
  hintTone,
  compact = false,
}: {
  label: string;
  value: string;
  hint?: string;
  hintTone?: "good" | "warn";
  compact?: boolean;
}) {
  const hintCls =
    hintTone === "good"
      ? "text-emerald-600"
      : hintTone === "warn"
      ? "text-amber-600"
      : "text-slate-500";
  return (
    <div className={`rounded-xl border border-line/70 bg-white ${compact ? "p-4" : "p-5"}`}>
      <p className="eyebrow">{label}</p>
      <p className={`mt-2 font-semibold tracking-tight ${compact ? "text-2xl" : "text-3xl"}`}>
        {value}
      </p>
      {hint ? <p className={`mt-1 text-xs ${hintCls}`}>{hint}</p> : null}
    </div>
  );
}

function fmt(v: number | null): string {
  if (v === null || v === undefined) return "n/a";
  return v.toFixed(2);
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}
