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
  const [policyOpen, setPolicyOpen] = useState(false);
  const [patientOpen, setPatientOpen] = useState(false);

  const selectedPolicy = useMemo(
    () => policies.find((p) => p.id === policyId) ?? policies[0],
    [policies, policyId]
  );
  const selectedPatient = useMemo(
    () => patients.find((p) => p.id === patientId) ?? patients[0],
    [patients, patientId]
  );

  const chartPreview = useMemo(() => {
    if (!selectedPatient) return "Paste FHIR Bundle JSON below to ingest a new patient.";
    const lines = selectedPatient.raw_chart.split("\n").slice(1, 5);
    return lines.join(" · ");
  }, [selectedPatient]);

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
    try {
      const det = await api.determine(patientId, policyId);
      router.push(`/results/${det.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="grid gap-5 md:grid-cols-2">
        <Selector
          eyebrow="Policy"
          title={selectedPolicy?.procedure_name ?? "No policies ingested"}
          subtitle={selectedPolicy ? policySubtitle(selectedPolicy) : "Ingest one on /policies"}
          open={policyOpen}
          onToggle={() => setPolicyOpen((v) => !v)}
        >
          {policies.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => {
                  setPolicyId(p.id);
                  setPolicyOpen(false);
                }}
                className={`flex w-full items-baseline justify-between gap-3 px-4 py-2 text-left text-sm hover:bg-slate-50 ${
                  p.id === policyId ? "bg-slate-50" : ""
                }`}
              >
                <span className="font-medium">{p.procedure_name}</span>
                <span className="font-mono text-xs text-slate-500">
                  {policySubtitle(p)}
                </span>
              </button>
            </li>
          ))}
        </Selector>

        <Selector
          eyebrow="Patient case"
          title={selectedPatient?.id ?? "No patients ingested"}
          subtitle={
            selectedPatient
              ? `${selectedPatient.age}${selectedPatient.sex} · ${patientHeadline(selectedPatient)}`
              : "Paste a FHIR Bundle below"
          }
          open={patientOpen}
          onToggle={() => setPatientOpen((v) => !v)}
        >
          {patients.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => {
                  setPatientId(p.id);
                  setPatientOpen(false);
                }}
                className={`flex w-full items-baseline justify-between gap-3 px-4 py-2 text-left text-sm hover:bg-slate-50 ${
                  p.id === patientId ? "bg-slate-50" : ""
                }`}
              >
                <span className="font-medium">{p.id}</span>
                <span className="font-mono text-xs text-slate-500">
                  {p.age}
                  {p.sex} · {patientHeadline(p)}
                </span>
              </button>
            </li>
          ))}
        </Selector>
      </div>

      <div className="rounded-xl border border-line/70 bg-white p-5">
        <p className="eyebrow mb-2">Or paste chart text</p>
        <textarea
          value={bundleText}
          onChange={(e) => setBundleText(e.target.value)}
          className="block h-28 w-full resize-y border-0 bg-transparent p-0 font-mono text-[13px] leading-relaxed text-slate-700 placeholder:text-slate-400 focus:outline-none"
          placeholder='{"resourceType":"Bundle", "entry":[...]}'
        />
        <div className="mt-2 flex items-center justify-between text-xs">
          <span className="text-slate-500">{!bundleText ? chartPreview : "JSON ready to ingest"}</span>
          <button
            type="button"
            onClick={ingestBundle}
            disabled={!bundleText.trim()}
            className="text-slate-500 underline-offset-2 hover:text-ink hover:underline disabled:opacity-40"
          >
            Ingest patient
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={run}
          disabled={busy || !patientId || !policyId}
          className="inline-flex items-center gap-2 rounded-md bg-ink px-5 py-3 text-sm font-medium text-white disabled:opacity-40"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
          {busy ? "Running..." : "Run determination"}
        </button>
        <span className="text-xs text-slate-500">
          Estimated 40-60 seconds · ~$0.09
        </span>
        {err ? <span className="text-xs text-red-600">{err}</span> : null}
      </div>
    </div>
  );
}

function Selector({
  eyebrow,
  title,
  subtitle,
  open,
  onToggle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <p className="eyebrow mb-2">{eyebrow}</p>
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between rounded-xl border border-line/70 bg-white px-4 py-4 text-left hover:border-line"
      >
        <div>
          <div className="text-[15px] font-medium">{title}</div>
          <div className="mt-0.5 text-xs text-slate-500">{subtitle}</div>
        </div>
        <svg viewBox="0 0 20 20" className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} fill="none">
          <path
            d="M5 8l5 5 5-5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {open ? (
        <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-line/70 bg-white shadow-lg">
          {children}
        </ul>
      ) : null}
    </div>
  );
}
