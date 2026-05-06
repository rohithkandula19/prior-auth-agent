"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  CriterionEvaluation,
  Patient,
  Policy,
} from "@/lib/types";

type Span = { start: number; end: number; key: string; tone: "policy" | "chart" };

function mergeSpans(spans: Span[]): Span[] {
  return [...spans].sort((a, b) => a.start - b.start);
}

/** Render text with highlighted spans. Active spans get a stronger outline. */
function HighlightedText({
  text,
  spans,
  activeKey,
  onSpanClick,
  scrollAnchorRefs,
}: {
  text: string;
  spans: Span[];
  activeKey: string | null;
  onSpanClick: (key: string) => void;
  scrollAnchorRefs?: React.MutableRefObject<Record<string, HTMLSpanElement | null>>;
}) {
  const sorted = useMemo(() => mergeSpans(spans), [spans]);
  const out: React.ReactNode[] = [];
  let cursor = 0;

  sorted.forEach((s, i) => {
    if (s.start < cursor) return; // skip overlap
    if (s.start > cursor) out.push(<span key={`t-${i}-pre`}>{text.slice(cursor, s.start)}</span>);
    const isActive = s.key === activeKey;
    out.push(
      <span
        key={`s-${i}`}
        ref={(el) => {
          if (scrollAnchorRefs) scrollAnchorRefs.current[s.key] = el;
        }}
        onClick={() => onSpanClick(s.key)}
        className={`${s.tone === "policy" ? "cite-policy" : "cite-chart"} cursor-pointer ${
          isActive ? "cite-active" : ""
        }`}
      >
        {text.slice(s.start, s.end)}
      </span>
    );
    cursor = s.end;
  });
  if (cursor < text.length) out.push(<span key="tail">{text.slice(cursor)}</span>);
  return <>{out}</>;
}

export function CitationViewer({
  policy,
  patient,
  evaluations,
}: {
  policy: Policy;
  patient: Patient;
  evaluations: CriterionEvaluation[];
}) {
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const policyRefs = useRef<Record<string, HTMLSpanElement | null>>({});
  const chartRefs = useRef<Record<string, HTMLSpanElement | null>>({});

  const policySpans: Span[] = evaluations.map((e) => ({
    start: e.policy_citation[0],
    end: e.policy_citation[1],
    key: `${e.criterion_id}::policy`,
    tone: "policy",
  }));

  const chartSpans: Span[] = evaluations.flatMap((e) =>
    e.chart_citations.map((c, idx) => ({
      start: c[0],
      end: c[1],
      key: `${e.criterion_id}::chart::${idx}`,
      tone: "chart" as const,
    }))
  );

  // When a criterion is selected, scroll its policy span and first chart span into view
  useEffect(() => {
    if (!activeKey) return;
    const [crit] = activeKey.split("::");
    const pkey = `${crit}::policy`;
    const ckey0 = `${crit}::chart::0`;
    policyRefs.current[pkey]?.scrollIntoView({ behavior: "smooth", block: "center" });
    chartRefs.current[ckey0]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeKey]);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-md border border-line bg-white">
        <div className="flex items-center justify-between border-b border-line px-4 py-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Policy
          </span>
          <span className="text-xs text-slate-500">{policy.payer} | {policy.procedure_name}</span>
        </div>
        <pre className="h-[60vh] overflow-auto whitespace-pre-wrap px-4 py-3 font-mono text-xs leading-relaxed">
          <HighlightedText
            text={policy.raw_text}
            spans={policySpans}
            activeKey={activeKey}
            onSpanClick={setActiveKey}
            scrollAnchorRefs={policyRefs}
          />
        </pre>
      </div>

      <div className="rounded-md border border-line bg-white">
        <div className="flex items-center justify-between border-b border-line px-4 py-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Patient chart
          </span>
          <span className="text-xs text-slate-500">{patient.id} | age {patient.age}</span>
        </div>
        <pre className="h-[60vh] overflow-auto whitespace-pre-wrap px-4 py-3 font-mono text-xs leading-relaxed">
          <HighlightedText
            text={patient.raw_chart}
            spans={chartSpans}
            activeKey={activeKey}
            onSpanClick={setActiveKey}
            scrollAnchorRefs={chartRefs}
          />
        </pre>
      </div>
    </div>
  );
}
