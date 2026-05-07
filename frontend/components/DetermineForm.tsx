"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Patient, Policy } from "@/lib/types";

function patientHeadline(p: Patient): string {
  const top = p.evidence.find((e) => e.type === "diagnosis")?.description;
  return top ? top : "Patient";
}

function policySubtitle(p: Policy): string {
  const required = p.criteria.filter((c) => c.type === "required").length;
  return `CPT ${p.procedure_code} · ${required} criteria`;
}

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
  const [progress, setProgress] = useState<{
    i: number;
    total: number;
    last_id?: string;
    last_status?: string;
    phase?: string;
  } | null>(null);

  const selectedPolicy = useMemo(
    () => policies.find((p) => p.id === policyId) ?? policies[0],
    [policies, policyId]
  );
  const selectedPatient = useMemo(
    () => patients.find((p) => p.id === patientId) ?? patients[0],
    [patients, patientId]
  );

  async function ingestBundle() {
    setErr(null);
    try {
      const parsed = JSON.parse(bundleText);
      const patient = await api.createPatient(parsed);
      setPatientId(patient.id);
      router.refresh();
      setBundleText("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function run() {
    setErr(null);
    setBusy(true);
    setProgress({ i: 0, total: 0, phase: "Starting" });
    try {
      let determinationId: string | null = null;
      for await (const ev of api.determineStream(patientId, policyId)) {
        const evt = ev as Record<string, unknown>;
        const name = evt.event;
        if (name === "started") {
          setProgress({ i: 0, total: Number(evt.criteria_count) || 0, phase: "Checking criteria" });
        } else if (name === "criterion") {
          setProgress({
            i: Number(evt.i) || 0,
            total: Number(evt.total) || 0,
            last_id: String(evt.criterion_id),
            last_status: String(evt.status),
            phase: "Checking criteria",
          });
        } else if (name === "citations_verified") {
          setProgress((p) => (p ? { ...p, phase: "Verifying citations" } : p));
        } else if (name === "gaps") {
          setProgress((p) => (p ? { ...p, phase: "Identifying gaps" } : p));
        } else if (name === "calibrated") {
          setProgress((p) => (p ? { ...p, phase: "Calibrating decision" } : p));
        } else if (name === "done") {
          determinationId = String(evt.determination_id);
        }
      }
      if (determinationId) router.push(`/results/${determinationId}`);
      else throw new Error("Stream finished without a determination id");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
      setProgress(null);
    }
  }

  return (
    <div className="space-y-10">
      <div className="grid gap-6 md:grid-cols-2">
        <SelectorCard
          eyebrow="Policy"
          title={selectedPolicy?.procedure_name ?? "No policies ingested"}
          subtitle={selectedPolicy ? policySubtitle(selectedPolicy) : "Add one in /policies"}
        >
          <select
            value={policyId}
            onChange={(e) => setPolicyId(e.target.value)}
            className="mt-3 w-full rounded-md border border-rule bg-paper px-3 py-2 text-sm"
          >
            {policies.length === 0 ? <option value="">No policies ingested</option> : null}
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.procedure_name} | {p.payer}
              </option>
            ))}
          </select>
        </SelectorCard>

        <SelectorCard
          eyebrow="Patient case"
          title={selectedPatient?.id ?? "No patients ingested"}
          subtitle={
            selectedPatient
              ? `${selectedPatient.age}${selectedPatient.sex} · ${patientHeadline(selectedPatient)}`
              : "Paste a FHIR Bundle below"
          }
        >
          <select
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="mt-3 w-full rounded-md border border-rule bg-paper px-3 py-2 text-sm"
          >
            {patients.length === 0 ? <option value="">No patients ingested</option> : null}
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} | {p.age}
                {p.sex} | {patientHeadline(p)}
              </option>
            ))}
          </select>
        </SelectorCard>
      </div>

      <details className="surface px-7 py-6">
        <summary className="flex cursor-pointer items-center justify-between text-sm">
          <span className="eyebrow">Or paste a FHIR Bundle</span>
          <span className="text-xs text-soft">Optional</span>
        </summary>
        <textarea
          value={bundleText}
          onChange={(e) => setBundleText(e.target.value)}
          className="mt-4 block h-40 w-full resize-y rounded-md border border-rule bg-paper px-3 py-2 font-mono text-[12px] leading-relaxed"
          placeholder='{"resourceType":"Bundle", "entry":[...]}'
        />
        <div className="mt-2 flex justify-end">
          <button
            type="button"
            onClick={ingestBundle}
            disabled={!bundleText.trim()}
            className="text-xs text-soft underline-offset-2 hover:text-ink hover:underline disabled:opacity-40"
          >
            Ingest patient
          </button>
        </div>
      </details>

      <div className="space-y-3">
        <div className="flex items-center gap-4">
          <button
            onClick={run}
            disabled={busy || !patientId || !policyId}
            className="inline-flex items-center gap-2 rounded-md bg-ink px-5 py-3 text-sm font-medium text-white disabled:opacity-30"
          >
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            {busy ? "Running..." : "Run determination"}
          </button>
          <span className="text-xs text-soft">
            Estimated 40-60 seconds · ~$0.09
          </span>
          {err ? <span className="text-xs text-red-700">{err}</span> : null}
        </div>

        {progress ? (
          <div className="surface px-6 py-5">
            <div className="flex items-baseline justify-between">
              <p className="text-sm font-medium text-ink">{progress.phase ?? "Working..."}</p>
              <p className="font-mono text-xs text-soft">
                {progress.i}/{progress.total}
              </p>
            </div>
            <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-rule">
              <div
                className="h-full rounded-full bg-ink transition-all"
                style={{
                  width: `${
                    progress.total > 0
                      ? Math.round((progress.i / progress.total) * 100)
                      : 4
                  }%`,
                }}
              />
            </div>
            {progress.last_id ? (
              <p className="mt-3 text-xs text-soft">
                Last <span className="font-mono">{progress.last_id}</span>{" "}
                <span className="text-rule">·</span> {progress.last_status}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SelectorCard({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="surface px-7 py-6">
      <p className="eyebrow">{eyebrow}</p>
      <p className="mt-2 text-[19px] font-medium tracking-tight text-ink">{title}</p>
      <p className="text-xs text-soft">{subtitle}</p>
      {children}
    </div>
  );
}
