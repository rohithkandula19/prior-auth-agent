"use client";

import { useMemo } from "react";
import type {
  CriterionEvaluation,
  Patient,
  Policy,
} from "@/lib/types";

const CONTEXT_CHARS = 220;

type Span = { start: number; end: number; key: string };

function mergeSpans(spans: Span[]): Span[] {
  if (spans.length === 0) return spans;
  const sorted = [...spans].sort((a, b) => a.start - b.start);
  const out: Span[] = [sorted[0]];
  for (const s of sorted.slice(1)) {
    const top = out[out.length - 1];
    if (s.start <= top.end) {
      top.end = Math.max(top.end, s.end);
      top.key = `${top.key}+${s.key}`;
    } else {
      out.push({ ...s });
    }
  }
  return out;
}

function clipAroundSpans(text: string, spans: Span[]): { text: string; spans: Span[] } {
  if (spans.length === 0) return { text: "", spans: [] };
  const merged = mergeSpans(spans);
  const minStart = Math.max(0, merged[0].start - 80);
  const maxEnd = Math.min(text.length, merged[merged.length - 1].end + 80);
  let from = minStart;
  let to = maxEnd;
  if (to - from > CONTEXT_CHARS * 1.5) {
    to = Math.min(text.length, from + CONTEXT_CHARS * 1.5);
  }
  // Move start/end to nearest sentence boundary if reasonable
  const slice = text.slice(from, to);
  const adjustedSpans = merged.map((s) => ({
    ...s,
    start: s.start - from,
    end: s.end - from,
  }));
  return { text: slice, spans: adjustedSpans };
}

function HighlightedExcerpt({
  text,
  spans,
  tone,
}: {
  text: string;
  spans: Span[];
  tone: "policy" | "chart";
}) {
  const out: React.ReactNode[] = [];
  let cursor = 0;
  spans.forEach((s, i) => {
    if (s.start < cursor) return;
    if (s.start > cursor) out.push(<span key={`t-${i}`}>{text.slice(cursor, s.start)}</span>);
    out.push(
      <mark
        key={`s-${i}`}
        className={tone === "policy" ? "cite-policy" : "cite-chart"}
      >
        {text.slice(s.start, s.end)}
      </mark>
    );
    cursor = s.end;
  });
  if (cursor < text.length) out.push(<span key="tail">{text.slice(cursor)}</span>);
  return <>{out}</>;
}

export function CitationCards({
  policy,
  patient,
  evaluations,
}: {
  policy: Policy;
  patient: Patient;
  evaluations: CriterionEvaluation[];
}) {
  const policyExcerpt = useMemo(() => {
    const spans: Span[] = evaluations
      .filter((e) => e.status === "met" || e.status === "partial")
      .map((e, i) => ({ start: e.policy_citation[0], end: e.policy_citation[1], key: `p${i}` }))
      .filter((s) => s.end > s.start);
    return clipAroundSpans(policy.raw_text, spans);
  }, [policy.raw_text, evaluations]);

  const chartExcerpt = useMemo(() => {
    const spans: Span[] = evaluations
      .filter((e) => e.status === "met" || e.status === "partial")
      .flatMap((e, i) =>
        e.chart_citations.map((c, j) => ({ start: c[0], end: c[1], key: `c${i}-${j}` }))
      )
      .filter((s) => s.end > s.start);
    return clipAroundSpans(patient.raw_chart, spans);
  }, [patient.raw_chart, evaluations]);

  const policyPage = evaluations[0]?.criterion_id
    ? policy.criteria.find((c) => c.id === evaluations[0].criterion_id)?.page_number
    : undefined;
  const visitDate = patient.evidence
    .map((e) => e.date)
    .sort()
    .at(-1);

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <article className="rounded-xl border border-line/70 bg-white p-6">
        <p className="eyebrow mb-3">Policy text</p>
        <p className="text-[15px] leading-relaxed text-slate-800">
          <HighlightedExcerpt
            text={policyExcerpt.text || policy.raw_text.slice(0, CONTEXT_CHARS)}
            spans={policyExcerpt.spans}
            tone="policy"
          />
        </p>
        <p className="mt-4 text-xs text-slate-500">
          {policy.payer} {policy.procedure_code}
          {policyPage ? ` · Page ${policyPage}` : null}
        </p>
      </article>

      <article className="rounded-xl border border-line/70 bg-white p-6">
        <p className="eyebrow mb-3">Chart text</p>
        <p className="text-[15px] leading-relaxed text-slate-800">
          <HighlightedExcerpt
            text={chartExcerpt.text || patient.raw_chart.slice(0, CONTEXT_CHARS)}
            spans={chartExcerpt.spans}
            tone="chart"
          />
        </p>
        <p className="mt-4 text-xs text-slate-500">
          Patient {patient.id}
          {visitDate ? ` · Visit ${visitDate}` : null}
        </p>
      </article>
    </div>
  );
}
