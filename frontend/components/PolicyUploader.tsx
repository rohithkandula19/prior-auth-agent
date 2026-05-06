"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function PolicyUploader() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [payer, setPayer] = useState("UnitedHealthcare");
  const [procedureCode, setProcedureCode] = useState("72148");
  const [procedureName, setProcedureName] = useState("MRI Lumbar Spine");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setErr(null);
    try {
      const policy = await api.ingestPolicyText({
        text,
        payer,
        procedure_code: procedureCode,
        procedure_name: procedureName,
      });
      router.refresh();
      setText("");
      router.push(`/policies?selected=${policy.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <input
          className="rounded-md border border-line px-3 py-2 text-sm"
          value={payer}
          onChange={(e) => setPayer(e.target.value)}
          placeholder="Payer"
        />
        <input
          className="rounded-md border border-line px-3 py-2 text-sm"
          value={procedureCode}
          onChange={(e) => setProcedureCode(e.target.value)}
          placeholder="CPT or HCPCS"
        />
        <input
          className="rounded-md border border-line px-3 py-2 text-sm"
          value={procedureName}
          onChange={(e) => setProcedureName(e.target.value)}
          placeholder="Procedure name"
        />
      </div>
      <textarea
        className="h-40 w-full rounded-md border border-line px-3 py-2 font-mono text-xs"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste policy text here. Calls Claude to extract structured criteria."
      />
      <div className="flex items-center justify-between">
        {err ? <span className="text-xs text-red-600">{err}</span> : <span />}
        <button
          onClick={submit}
          disabled={busy || !text.trim()}
          className="rounded-md bg-ink px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {busy ? "Extracting..." : "Ingest policy"}
        </button>
      </div>
    </div>
  );
}
