"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Patient, Policy } from "@/lib/types";

export function DetermineForm({
  policies,
  patients,
}: {
  policies: Policy[];
  patients: Patient[];
}) {
  const router = useRouter();
  const [policyId, setPolicyId] = useState(policies[0]?.id ?? "");
  const [patientId, setPatientId] = useState(patients[0]?.id ?? "");
  const [bundleText, setBundleText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function ingestBundle() {
    setErr(null);
    try {
      const parsed = JSON.parse(bundleText);
      const patient = await api.createPatient(parsed);
      setPatientId(patient.id);
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function run() {
    setErr(null);
    setBusy(true);
    try {
      const det = await api.determine(patientId, policyId);
      router.push(`/results/${det.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-3">
        <label className="block text-sm font-medium">Policy</label>
        <select
          value={policyId}
          onChange={(e) => setPolicyId(e.target.value)}
          className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
        >
          {policies.length === 0 ? <option value="">No policies ingested</option> : null}
          {policies.map((p) => (
            <option key={p.id} value={p.id}>
              {p.procedure_name} | {p.payer} | {p.id}
            </option>
          ))}
        </select>

        <label className="block pt-2 text-sm font-medium">Patient</label>
        <select
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
        >
          {patients.length === 0 ? <option value="">No patients ingested</option> : null}
          {patients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.id} | age {p.age} | {p.sex}
            </option>
          ))}
        </select>

        <button
          onClick={run}
          disabled={busy || !patientId || !policyId}
          className="w-full rounded-md bg-ink px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {busy ? "Running..." : "Run determination"}
        </button>
        {err ? <p className="text-xs text-red-600">{err}</p> : null}
      </div>

      <div className="space-y-3">
        <label className="block text-sm font-medium">Or paste a FHIR Bundle</label>
        <textarea
          value={bundleText}
          onChange={(e) => setBundleText(e.target.value)}
          className="h-64 w-full rounded-md border border-line px-3 py-2 font-mono text-xs"
          placeholder='{"resourceType":"Bundle", "entry":[...]}'
        />
        <button
          onClick={ingestBundle}
          disabled={!bundleText.trim()}
          className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
        >
          Ingest patient
        </button>
      </div>
    </div>
  );
}
