"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Mode = "upload" | "paste";

export function PolicyUploader() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("upload");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [payer, setPayer] = useState("UnitedHealthcare");
  const [procedureCode, setProcedureCode] = useState("72148");
  const [procedureName, setProcedureName] = useState("MRI Lumbar Spine");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  async function submit() {
    setBusy(true);
    setErr(null);
    try {
      const fields = {
        payer,
        procedure_code: procedureCode,
        procedure_name: procedureName,
      };
      const policy =
        mode === "upload" && file
          ? await api.ingestPolicyFile(file, fields)
          : await api.ingestPolicyText({ text, ...fields });
      router.refresh();
      setText("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      router.push(`/policies?selected=${policy.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }

  const canSubmit =
    !busy && ((mode === "upload" && file) || (mode === "paste" && text.trim()));

  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-3">
        <Field label="Payer" value={payer} onChange={setPayer} />
        <Field label="Procedure code" value={procedureCode} onChange={setProcedureCode} />
        <Field label="Procedure name" value={procedureName} onChange={setProcedureName} />
      </div>

      <div className="flex gap-6 border-b border-rule text-sm">
        <Tab active={mode === "upload"} onClick={() => setMode("upload")}>
          Upload PDF
        </Tab>
        <Tab active={mode === "paste"} onClick={() => setMode("paste")}>
          Paste text
        </Tab>
      </div>

      {mode === "upload" ? (
        <div
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
          className="rounded-xl border border-dashed border-rule bg-canvas px-8 py-12 text-center"
        >
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="hidden"
            id="policy-file-input"
          />
          {file ? (
            <p className="text-[15px] text-ink">
              <span className="font-medium">{file.name}</span>
              <span className="ml-2 text-soft">
                {Math.round(file.size / 1024)} KB
              </span>
            </p>
          ) : (
            <p className="text-[15px] text-body">
              Drop a PDF here, or{" "}
              <label
                htmlFor="policy-file-input"
                className="cursor-pointer text-ink underline underline-offset-4 hover:no-underline"
              >
                browse for a file
              </label>
              .
            </p>
          )}
          <p className="mt-3 text-xs text-soft">
            Accepts .pdf or .txt. The extractor calls the configured LLM to
            pull structured criteria.
          </p>
          {file ? (
            <button
              type="button"
              onClick={() => {
                setFile(null);
                if (fileInput.current) fileInput.current.value = "";
              }}
              className="mt-2 text-xs text-soft underline-offset-2 hover:text-ink hover:underline"
            >
              choose a different file
            </button>
          ) : null}
        </div>
      ) : (
        <textarea
          className="block h-56 w-full resize-y rounded-xl border border-rule bg-canvas px-5 py-4 font-mono text-[13px] leading-relaxed"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste policy text here. The extractor will pull structured criteria."
        />
      )}

      <div className="flex items-center justify-between gap-4">
        {err ? <span className="text-xs text-red-700">{err}</span> : <span />}
        <button
          onClick={submit}
          disabled={!canSubmit}
          className="rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-white disabled:opacity-30"
        >
          {busy ? "Extracting..." : "Ingest policy"}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="eyebrow">{label}</span>
      <input
        className="mt-1.5 w-full rounded-md border border-rule bg-canvas px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`-mb-px border-b-2 px-1 py-3 ${
        active
          ? "border-ink font-medium text-ink"
          : "border-transparent text-soft hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
