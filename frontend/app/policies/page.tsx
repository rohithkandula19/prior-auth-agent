import Link from "next/link";
import { api } from "@/lib/api";
import { PolicyUploader } from "@/components/PolicyUploader";

export const dynamic = "force-dynamic";

export default async function PoliciesPage() {
  let policies: Awaited<ReturnType<typeof api.listPolicies>> = [];
  let error: string | null = null;
  try {
    policies = await api.listPolicies();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-16">
      <header className="space-y-3">
        <p className="eyebrow">Policy library</p>
        <h1 className="h-display text-[44px] tracking-tightest">
          Ingested payer policies
        </h1>
        <p className="max-w-xl text-[15px] leading-relaxed text-body">
          Upload a payer PDF or paste raw policy text. The extractor pulls
          structured criteria with verbatim spans you can cite later.
        </p>
      </header>

      {error ? (
        <p className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Could not reach the API: {error}. Start the backend with{" "}
          <code className="font-mono text-xs">make run</code>.
        </p>
      ) : null}

      <section className="surface px-8 py-8">
        <div className="mb-6 flex items-baseline justify-between">
          <h2 className="text-[19px] font-medium tracking-tight">Ingest a new policy</h2>
          <p className="text-xs text-soft">PDF or pasted text</p>
        </div>
        <PolicyUploader />
      </section>

      <section className="space-y-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[19px] font-medium tracking-tight">
            {policies.length} {policies.length === 1 ? "policy" : "policies"}
          </h2>
          <p className="text-xs text-soft">Most recent first</p>
        </div>
        {policies.length === 0 ? (
          <p className="text-sm text-soft">
            Nothing ingested yet. Drop a PDF in the form above.
          </p>
        ) : (
          <ul className="divide-y divide-rule">
            {policies.map((p) => {
              const required = p.criteria.filter((c) => c.type === "required").length;
              const contra = p.criteria.filter((c) => c.type === "contraindication").length;
              const docs = p.criteria.filter((c) => c.type === "documentation").length;
              return (
                <li key={p.id} className="flex items-baseline justify-between gap-6 py-5">
                  <div className="min-w-0">
                    <Link
                      href={`/policies?selected=${p.id}`}
                      className="text-[19px] font-medium tracking-tight hover:underline underline-offset-4"
                    >
                      {p.procedure_name}
                    </Link>
                    <p className="mt-1 text-sm text-soft">
                      {p.payer} <span className="text-rule">·</span> CPT {p.procedure_code}{" "}
                      <span className="text-rule">·</span> effective {p.effective_date}
                    </p>
                    <p className="mt-1 text-xs text-soft">
                      Policy id <span className="font-mono">{p.id}</span>
                    </p>
                  </div>
                  <div className="flex flex-shrink-0 gap-5 font-mono text-xs text-soft">
                    <span>{required} req</span>
                    <span className="text-denied">{contra} contra</span>
                    <span>{docs} docs</span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
