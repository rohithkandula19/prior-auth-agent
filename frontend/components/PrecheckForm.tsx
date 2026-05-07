"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Policy } from "@/lib/types";

type PrecheckResult = Awaited<ReturnType<typeof api.precheck>>;

const SAMPLE = `52F with low back pain since August 2025.
Completed 8 weeks of physical therapy without sustained improvement.
Currently on naproxen 500 mg BID since September 2025.
Neuro exam 04/01/2025: normal motor and sensory throughout.
Lumbar XR 03/20/2025: mild degenerative changes.
No pacemaker or implanted defibrillator.`;

export function PrecheckForm({ policies }: { policies: Policy[] }) {
  const [policyId, setPolicyId] = useState(policies[0]?.id ?? "");
  const [note, setNote] = useState(SAMPLE);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<PrecheckResult | null>(null);

  async function run() {
    setErr(null);
    setBusy(true);
    setResult(null);
    try {
      const r = await api.precheck(policyId, note);
      setResult(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const decisionLabel: Record<string, { label: string; tone: string }> = {
    approved: { label: "Likely approved", tone: "text-approved" },
    denied: { label: "Likely denied", tone: "text-denied" },
    needs_more_info: { label: "Needs more info", tone: "text-pending" },
  };

  return (
    <div className="space-y-8">
      <div className="grid gap-6 md:grid-cols-[260px,1fr]">
        <div className="surface px-6 py-5">
          <p className="eyebrow">Policy</p>
          <select
            value={policyId}
            onChange={(e) => setPolicyId(e.target.value)}
            className="mt-3 w-full rounded-md border border-rule bg-paper px-3 py-2 text-sm"
          >
            {policies.length === 0 ? <option value="">No policies ingested</option> : null}
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.procedure_name}
              </option>
            ))}
          </select>
        </div>

        <div className="surface px-6 py-5">
          <p className="eyebrow">Draft note</p>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="mt-3 block h-56 w-full resize-y rounded-md border border-rule bg-paper px-3 py-2 font-mono text-[12px] leading-relaxed"
            placeholder="Paste the visit note you plan to attach to the PA packet."
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={run}
          disabled={busy || !policyId || !note.trim()}
          className="rounded-md bg-ink px-5 py-2.5 text-sm font-medium text-white disabled:opacity-30"
        >
          {busy ? "Checking..." : "Check before submitting"}
        </button>
        <span className="text-xs text-soft">~40 seconds · same agent as /determine</span>
        {err ? <span className="text-xs text-red-700">{err}</span> : null}
      </div>

      {result ? (
        <div className="space-y-8">
          <div className="surface px-7 py-6">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="eyebrow">Predicted outcome</p>
                <p
                  className={`mt-2 h-display text-[34px] ${
                    decisionLabel[result.likely_decision]?.tone ?? "text-ink"
                  }`}
                >
                  {decisionLabel[result.likely_decision]?.label ?? result.likely_decision}
                </p>
              </div>
              <div className="text-right">
                <p className="eyebrow">Confidence</p>
                <p className="mt-2 h-display text-[28px] text-ink">
                  {result.confidence.toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          {result.add_before_submitting.length > 0 ? (
            <section className="space-y-4">
              <p className="eyebrow">Add before submitting</p>
              <ul className="divide-y divide-rule rounded-xl bg-canvas px-2">
                {result.add_before_submitting.map((item) => (
                  <li key={item.criterion_id} className="px-5 py-4">
                    <p className="text-[15px] font-medium text-ink">{item.title}</p>
                    <p className="mt-1 text-sm text-body">{item.why}</p>
                    <p className="mt-1 font-mono text-xs text-soft">{item.criterion_id}</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <p className="text-sm text-approved">
              No blocking items. Submit when you are ready.
            </p>
          )}

          {result.will_clear.length > 0 ? (
            <section className="space-y-4">
              <p className="eyebrow">Will clear</p>
              <ul className="space-y-2 text-sm text-body">
                {result.will_clear.map((item) => (
                  <li key={item.criterion_id} className="flex items-baseline gap-3">
                    <span className="font-mono text-xs text-soft">{item.criterion_id}</span>
                    <span className="text-ink">{item.title}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <p className="text-xs text-soft">
            Full determination saved as{" "}
            <Link
              href={`/results/${result.determination.id}`}
              className="underline underline-offset-4 hover:text-ink"
            >
              {result.determination.id}
            </Link>
          </p>
        </div>
      ) : null}
    </div>
  );
}
