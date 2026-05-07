"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type CompareResult = Awaited<ReturnType<typeof api.compareModels>>;

const DEFAULT_MODELS = [
  "qwen/qwen-2.5-72b-instruct",
  "meta-llama/llama-3.3-70b-instruct",
  "deepseek/deepseek-chat",
];

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return "-";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)} ms`;
}

function fmt(v: number | null | undefined, digits = 2): string {
  if (v == null) return "-";
  return v.toFixed(digits);
}

function fmtDelta(v: number | null | undefined, digits = 2): string {
  if (v == null) return "-";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}`;
}

function deltaTone(v: number | null | undefined, lowerIsBetter = false): string {
  if (v == null || v === 0) return "text-soft";
  const better = lowerIsBetter ? v < 0 : v > 0;
  return better ? "text-approved" : "text-denied";
}

export function ModelCompare() {
  const [modelsText, setModelsText] = useState(DEFAULT_MODELS.join("\n"));
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<CompareResult | null>(null);

  async function run() {
    setRunning(true);
    setErr(null);
    setResult(null);
    try {
      const models = modelsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      if (models.length < 2) throw new Error("Provide at least two models, one per line.");
      const r = await api.compareModels(models);
      setResult(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex items-baseline justify-between">
        <p className="eyebrow">A/B model comparison</p>
        <button
          onClick={run}
          disabled={running}
          className="rounded-md border border-rule bg-canvas px-3 py-2 text-sm hover:border-ink/40 disabled:opacity-30"
        >
          {running ? "Running..." : "Compare"}
        </button>
      </div>
      <textarea
        value={modelsText}
        onChange={(e) => setModelsText(e.target.value)}
        className="block h-24 w-full resize-y rounded-md border border-rule bg-canvas px-3 py-2 font-mono text-[12px] leading-relaxed"
        placeholder="One OpenRouter model id per line"
      />
      <p className="text-xs text-soft">
        First line is the baseline. The eval runs the same gold set against
        each model and reports per-model agreement, calibration, latency,
        and cost, plus deltas vs the baseline.
      </p>
      {err ? <p className="text-xs text-red-700">{err}</p> : null}

      {result ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-rule text-left">
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 pr-4 font-medium">Agreement</th>
                <th className="py-2 pr-4 font-medium">ECE</th>
                <th className="py-2 pr-4 font-medium">p95 latency</th>
                <th className="py-2 pr-4 font-medium">Avg cost</th>
              </tr>
            </thead>
            <tbody>
              {result.models.map((m) => {
                const r = result.by_model[m];
                const d = result.deltas[m];
                const isBaseline = m === result.baseline;
                return (
                  <tr key={m} className="border-b border-rule/50">
                    <td className="py-3 pr-4">
                      <div className="font-mono text-[12px]">{m}</div>
                      {isBaseline ? (
                        <div className="mt-0.5 text-[10px] uppercase tracking-wider text-soft">
                          baseline
                        </div>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="font-medium">{fmt(r.agreement, 3)}</span>
                      {!isBaseline && d ? (
                        <span className={`ml-2 text-xs ${deltaTone(d.agreement_diff)}`}>
                          {fmtDelta(d.agreement_diff, 3)}
                        </span>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="font-medium">{fmt(r.ece, 3)}</span>
                      {!isBaseline && d ? (
                        <span className={`ml-2 text-xs ${deltaTone(d.ece_diff, true)}`}>
                          {fmtDelta(d.ece_diff, 3)}
                        </span>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="font-medium">{formatMs(r.latency_ms?.p95)}</span>
                      {!isBaseline && d?.p95_latency_diff_ms != null ? (
                        <span className={`ml-2 text-xs ${deltaTone(d.p95_latency_diff_ms, true)}`}>
                          {fmtDelta(d.p95_latency_diff_ms, 0)} ms
                        </span>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="font-medium">${fmt(r.avg_cost_usd, 4)}</span>
                      {!isBaseline && d?.cost_diff_usd != null ? (
                        <span className={`ml-2 text-xs ${deltaTone(d.cost_diff_usd, true)}`}>
                          {fmtDelta(d.cost_diff_usd, 4)}
                        </span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
