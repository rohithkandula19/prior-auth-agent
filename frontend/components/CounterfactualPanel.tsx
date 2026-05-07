"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Counterfactual = Awaited<ReturnType<typeof api.counterfactuals>>[number];

const DECISION_TONE: Record<string, string> = {
  approved: "text-approved",
  denied: "text-denied",
  needs_more_info: "text-pending",
};

export function CounterfactualPanel({ determinationId }: { determinationId: string }) {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<Counterfactual[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setErr(null);
    try {
      const r = await api.counterfactuals(determinationId);
      setItems(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="surface px-8 py-7">
      <div className="flex items-baseline justify-between">
        <p className="eyebrow">What would flip this?</p>
        {items && items.length > 0 ? (
          <span className="text-xs text-soft">{items.length} suggestion{items.length === 1 ? "" : "s"}</span>
        ) : null}
      </div>
      {!items ? (
        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={generate}
            disabled={loading}
            className="rounded-md border border-rule bg-canvas px-4 py-2 text-sm hover:border-ink/40 disabled:opacity-30"
          >
            {loading ? "Analyzing..." : "Show counterfactuals"}
          </button>
          <span className="text-xs text-soft">
            One concrete fact that, if added to the chart, would change the
            decision. Useful for guiding the next visit.
          </span>
          {err ? <span className="text-xs text-red-700">{err}</span> : null}
        </div>
      ) : items.length === 0 ? (
        <p className="mt-4 text-sm text-soft">
          No realistic counterfactual would change this decision.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-rule">
          {items.map((c, i) => (
            <li key={i} className="py-4">
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[15px] font-medium text-ink">{c.add_to_chart}</p>
                <span className="font-mono text-xs text-soft">{c.target_criterion_id}</span>
              </div>
              <p className="mt-1 text-sm text-body">{c.rationale}</p>
              <p className="mt-1 text-xs text-soft">
                If added: criterion goes <span className="text-ink">{c.expected_status_after}</span>{" "}
                <span className="text-rule">·</span> decision becomes{" "}
                <span className={DECISION_TONE[c.predicted_decision_after] ?? "text-ink"}>
                  {c.predicted_decision_after.replace(/_/g, " ")}
                </span>
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
