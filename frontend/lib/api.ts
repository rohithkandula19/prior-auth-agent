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
  getDetermination: (id: string) => request<Determination>(`/determinations/${id}`),
  listDeterminations: () => request<Determination[]>("/determinations"),

  metrics: () => request<EvalSummary>("/eval/metrics"),
  runEval: (limit?: number) =>
    request<{ run_id: string; n: number; agreement: number; summary: EvalSummary }>(
      "/eval/run",
      { method: "POST", body: JSON.stringify({ limit }) }
    ),
};
