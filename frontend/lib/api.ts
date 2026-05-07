import type {
  Determination,
  EvalSummary,
  Patient,
  Policy,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listPolicies: () => request<Policy[]>("/policies"),
  getPolicy: (id: string) => request<Policy>(`/policies/${id}`),
  ingestPolicyText: (body: {
    text: string;
    payer?: string;
    procedure_code?: string;
    procedure_name?: string;
    effective_date?: string;
    source_url?: string;
    policy_id?: string;
    skip_embeddings?: boolean;
  }) =>
    request<Policy>("/policies/ingest_text", {
      method: "POST",
      body: JSON.stringify({ skip_embeddings: true, ...body }),
    }),

  ingestPolicyFile: async (
    file: File,
    fields: {
      payer?: string;
      procedure_code?: string;
      procedure_name?: string;
      effective_date?: string;
      source_url?: string;
      policy_id?: string;
      skip_embeddings?: boolean;
    } = {}
  ): Promise<Policy> => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("payer", fields.payer ?? "UnitedHealthcare");
    fd.append("procedure_code", fields.procedure_code ?? "72148");
    fd.append("procedure_name", fields.procedure_name ?? "MRI Lumbar Spine");
    fd.append("effective_date", fields.effective_date ?? "2025-01-01");
    fd.append("source_url", fields.source_url ?? "");
    if (fields.policy_id) fd.append("policy_id", fields.policy_id);
    fd.append("skip_embeddings", String(fields.skip_embeddings ?? true));
    const res = await fetch(`${BASE}/policies/ingest`, {
      method: "POST",
      body: fd,
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
    return res.json() as Promise<Policy>;
  },

  listPatients: () => request<Patient[]>("/patients"),
  getPatient: (id: string) => request<Patient>(`/patients/${id}`),
  createPatient: (fhirBundle: unknown, patient_id?: string) =>
    request<Patient>("/patients", {
      method: "POST",
      body: JSON.stringify({ fhir_bundle: fhirBundle, patient_id }),
    }),

  determine: (patient_id: string, policy_id: string) =>
    request<Determination>("/determine", {
      method: "POST",
      body: JSON.stringify({ patient_id, policy_id }),
    }),

  determineStream: async function* (
    patient_id: string,
    policy_id: string
  ): AsyncGenerator<Record<string, unknown>, void, unknown> {
    const res = await fetch(`${BASE}/determine/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id, policy_id }),
      cache: "no-store",
    });
    if (!res.ok || !res.body) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          yield JSON.parse(line);
        } catch {
          // skip malformed line
        }
      }
    }
    if (buffer.trim()) {
      try {
        yield JSON.parse(buffer);
      } catch {
        // ignore
      }
    }
  },
  getDetermination: (id: string) => request<Determination>(`/determinations/${id}`),
  listDeterminations: () => request<Determination[]>("/determinations"),

  precheck: (policy_id: string, note: string, age?: number, sex?: string) =>
    request<{
      determination: Determination;
      likely_decision: string;
      add_before_submitting: { criterion_id: string; title: string; why: string }[];
      will_clear: { criterion_id: string; title: string; why: string }[];
      confidence: number;
    }>("/precheck", {
      method: "POST",
      body: JSON.stringify({ policy_id, note, age, sex }),
    }),

  appeal: (determination_id: string) =>
    request<{ letter: string; cost_usd: number; latency_ms: number }>(
      `/determinations/${determination_id}/appeal`,
      { method: "POST", body: JSON.stringify({}) }
    ),

  counterfactuals: (determination_id: string) =>
    request<
      {
        target_criterion_id: string;
        add_to_chart: string;
        expected_status_after: string;
        predicted_decision_after: string;
        rationale: string;
      }[]
    >(`/determinations/${determination_id}/counterfactuals`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  metrics: () => request<EvalSummary>("/eval/metrics"),
  runEval: (limit?: number) =>
    request<{ run_id: string; n: number; agreement: number; summary: EvalSummary }>(
      "/eval/run",
      { method: "POST", body: JSON.stringify({ limit }) }
    ),
  compareModels: (models: string[], limit?: number) =>
    request<{
      baseline: string;
      models: string[];
      by_model: Record<
        string,
        {
          n: number;
          agreement: number;
          ece: number | null;
          latency_ms: { p50: number; p95: number; p99: number } | null;
          avg_cost_usd: number | null;
        }
      >;
      deltas: Record<
        string,
        {
          agreement_diff: number | null;
          ece_diff: number | null;
          p95_latency_diff_ms: number | null;
          cost_diff_usd: number | null;
        }
      >;
    }>("/eval/compare", { method: "POST", body: JSON.stringify({ models, limit }) }),
};
