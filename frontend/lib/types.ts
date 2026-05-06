// Mirrors backend Pydantic schemas. Keep in sync with backend/app/schemas/.

export type CriterionType = "required" | "contraindication" | "documentation";

export interface Criterion {
  id: string;
  text: string;
  type: CriterionType;
  parent_id: string | null;
  page_number: number;
  char_span: [number, number];
}

export interface Policy {
  id: string;
  payer: string;
  procedure_code: string;
  procedure_name: string;
  effective_date: string;
  source_url: string;
  raw_text: string;
  criteria: Criterion[];
  embedding_index_path: string | null;
}

export type EvidenceType =
  | "diagnosis"
  | "medication"
  | "procedure"
  | "lab"
  | "imaging"
  | "note";

export interface ClinicalEvidence {
  id: string;
  type: EvidenceType;
  code: string | null;
  description: string;
  date: string;
  source_text: string;
  char_span: [number, number];
}

export interface Patient {
  id: string;
  age: number;
  sex: string;
  evidence: ClinicalEvidence[];
  raw_chart: string;
}

export type CriterionStatus =
  | "met"
  | "not_met"
  | "partial"
  | "insufficient_evidence";

export type DecisionType = "approved" | "denied" | "needs_more_info";

export interface CriterionEvaluation {
  criterion_id: string;
  status: CriterionStatus;
  supporting_evidence: string[];
  policy_citation: [number, number];
  chart_citations: [number, number][];
  reasoning: string;
}

export interface Determination {
  id: string;
  patient_id: string;
  policy_id: string;
  decision: DecisionType;
  confidence: number;
  criterion_evaluations: CriterionEvaluation[];
  gaps: string[];
  recommended_action: string;
  latency_ms: number;
  cost_usd: number;
  created_at: string;
}

export interface EvalSummary {
  run_version?: string;
  n: number;
  agreement: number;
  ece?: number;
  reliability?: { bin: string; count: number; accuracy: number; avg_confidence: number }[];
  by_decision?: Record<string, { n: number; correct: number; accuracy: number }>;
  latency_ms?: { p50: number; p95: number; p99: number };
  avg_cost_usd?: number;
  failure_modes?: Record<string, { count: number; pct: number }> | Record<string, number>;
}
