"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function AppealPanel({ determinationId }: { determinationId: string }) {
  const [loading, setLoading] = useState(false);
  const [letter, setLetter] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ cost: number; ms: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function generate() {
    setLoading(true);
    setErr(null);
    try {
      const r = await api.appeal(determinationId);
      setLetter(r.letter);
      setMeta({ cost: r.cost_usd, ms: r.latency_ms });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    if (!letter) return;
    try {
      await navigator.clipboard.writeText(letter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  return (
    <section className="surface px-8 py-7">
      <div className="flex items-baseline justify-between gap-4">
        <p className="eyebrow">Appeal letter</p>
        {letter ? (
          <button
            onClick={copy}
            className="text-xs text-soft underline-offset-2 hover:text-ink hover:underline"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        ) : null}
      </div>
      {!letter ? (
        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={generate}
            disabled={loading}
            className="rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-white disabled:opacity-30"
          >
            {loading ? "Drafting..." : "Draft appeal letter"}
          </button>
          <span className="text-xs text-soft">
            Cites the policy and chart spans verbatim. Provider edits before
            sending.
          </span>
          {err ? <span className="text-xs text-red-700">{err}</span> : null}
        </div>
      ) : (
        <>
          <pre className="mt-4 max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-md bg-canvas px-5 py-4 font-sans text-[14px] leading-relaxed text-ink">
            {letter}
          </pre>
          {meta ? (
            <p className="mt-2 text-xs text-soft">
              Generated in {meta.ms} ms · ${meta.cost.toFixed(4)}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
