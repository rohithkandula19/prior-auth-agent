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
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <input
          className="rounded-md border border-line/70 bg-white px-3 py-2 text-sm"
          value={payer}
          onChange={(e) => setPayer(e.target.value)}
          placeholder="Payer"
        />
        <input
          className="rounded-md border border-line/70 bg-white px-3 py-2 text-sm"
          value={procedureCode}
          onChange={(e) => setProcedureCode(e.target.value)}
          placeholder="CPT or HCPCS"
        />
        <input
          className="rounded-md border border-line/70 bg-white px-3 py-2 text-sm"
          value={procedureName}
          onChange={(e) => setProcedureName(e.target.value)}
          placeholder="Procedure name"
        />
      </div>

      <div className="flex gap-1 border-b border-line/70 text-sm">
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
          className="rounded-lg border border-dashed border-line/80 bg-white px-6 py-10 text-center"
        >
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="hidden"
            id="policy-file-input"
          />
          <p className="text-sm text-slate-700">
            {file ? (
              <>
                <span className="font-medium">{file.name}</span>{" "}
                <span className="text-slate-500">
                  ({Math.round(file.size / 1024)} KB)
                </span>
              </>
            ) : (
              "Drop a PDF here, or"
            )}
          </p>
          <label
            htmlFor="policy-file-input"
            className="mt-2 inline-block cursor-pointer text-sm text-slate-500 underline-offset-2 hover:text-ink hover:underline"
          >
            {file ? "Choose a different file" : "browse for a file"}
          </label>
          <p className="mt-3 text-xs text-slate-400">
            Accepts .pdf or .txt. The extractor calls the configured LLM to
            pull structured criteria.
          </p>
        </div>
      ) : (
        <textarea
          className="h-48 w-full resize-y rounded-md border border-line/70 bg-white px-3 py-2 font-mono text-xs leading-relaxed"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste policy text here. The extractor will pull structured criteria."
        />
      )}

      <div className="flex items-center justify-between">
        {err ? <span className="text-xs text-red-600">{err}</span> : <span />}
        <button
          onClick={submit}
          disabled={!canSubmit}
          className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {busy ? "Extracting..." : "Ingest policy"}
        </button>
      </div>
    </div>
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
      className={`-mb-px border-b-2 px-3 py-2 ${
        active
          ? "border-ink font-medium text-ink"
          : "border-transparent text-slate-500 hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
