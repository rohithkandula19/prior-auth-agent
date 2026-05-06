"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { EvalSummary } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";

function ReliabilityChart({
  rows,
}: {
  rows: NonNullable<EvalSummary["reliability"]>;
}) {
  const max = 1.0;
  return (
    <div className="space-y-2">
      {rows.length === 0 ? (
        <div className="text-xs text-slate-500">No reliability data.</div>
      ) : (
        rows.map((r) => (
          <div key={r.bin} className="grid grid-cols-12 items-center gap-2 text-xs">
            <span className="col-span-2 font-mono text-slate-500">{r.bin}</span>
            <div className="col-span-7 h-4 rounded bg-slate-100">
              <div
                className="h-full rounded bg-emerald-500/70"
                style={{ width: `${(r.accuracy / max) * 100}%` }}
                title={`accuracy ${r.accuracy}`}
              />
              <div
                className="-mt-4 h-4 rounded border-r-2 border-blue-500"
                style={{ width: `${(r.avg_confidence / max) * 100}%` }}
                title={`avg confidence ${r.avg_confidence}`}
              />
            </div>
            <span className="col-span-1 font-mono text-right text-slate-500">{r.count}</span>
            <span className="col-span-2 font-mono text-right text-slate-500">
              {r.accuracy.toFixed(2)} / {r.avg_confidence.toFixed(2)}
            </span>
          </div>
        ))
      )}
      <div className="flex justify-end gap-3 pt-1 text-[10px] text-slate-500">
        <span>green = accuracy</span>
        <span>blue line = avg confidence</span>
      </div>
    </div>
  );
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Eval dashboard</h1>
          <p className="text-sm text-slate-600">
            Latest agreement, calibration, latency, and failure modes from the
            stub gold set.
          </p>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="rounded-md bg-ink px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {running ? "Running..." : "Run eval"}
        </button>
      </div>
      {err ? <p className="text-xs text-red-600">{err}</p> : null}

      <div className="grid gap-3 md:grid-cols-4">
        <Stat label="Cases" value={String(summary.n)} />
        <Stat label="Agreement" value={(summary.agreement ?? 0).toFixed(3)} />
        <Stat label="ECE" value={(summary.ece ?? 0).toFixed(3)} />
        <Stat
          label="Avg cost"
          value={`$${(summary.avg_cost_usd ?? 0).toFixed(4)}`}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-line bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold">Reliability diagram</h3>
          <ReliabilityChart rows={summary.reliability ?? []} />
        </div>
        <div className="rounded-lg border border-line bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold">Latency (ms)</h3>
          <div className="grid grid-cols-3 gap-3 text-center">
            <Stat
              label="p50"
              value={String(summary.latency_ms?.p50 ?? 0)}
              compact
            />
            <Stat
              label="p95"
              value={String(summary.latency_ms?.p95 ?? 0)}
              compact
            />
            <Stat
              label="p99"
              value={String(summary.latency_ms?.p99 ?? 0)}
              compact
            />
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-line bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold">By decision</h3>
          {summary.by_decision && Object.keys(summary.by_decision).length > 0 ? (
            <ul className="space-y-2 text-sm">
              {Object.entries(summary.by_decision).map(([d, v]) => (
                <li key={d} className="flex items-center justify-between">
                  <Badge
                    tone={
                      d === "approved"
                        ? "approved"
                        : d === "denied"
                        ? "denied"
                        : "pending"
                    }
                  >
                    {d}
                  </Badge>
                  <span className="font-mono text-xs text-slate-600">
                    {v.n} cases | accuracy {v.accuracy.toFixed(3)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">No data yet.</p>
          )}
        </div>
        <div className="rounded-lg border border-line bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold">Failure modes</h3>
          {summary.failure_modes && Object.keys(summary.failure_modes).length > 0 ? (
            <ul className="space-y-1 text-sm">
              {Object.entries(summary.failure_modes).map(([k, v]) => (
                <li key={k} className="flex items-center justify-between">
                  <span>{k.replace(/_/g, " ")}</span>
                  <span className="font-mono text-xs text-slate-600">{v}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">No failures detected.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border border-line bg-white ${
        compact ? "px-3 py-2" : "p-5"
      }`}
    >
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 font-semibold ${compact ? "text-lg" : "text-2xl"}`}>
        {value}
      </div>
    </div>
  );
}
