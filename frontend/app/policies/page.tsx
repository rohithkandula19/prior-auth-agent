import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
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
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Policy library</h1>
        <p className="text-sm text-slate-600">
          Ingested payer policies with their structured criteria. Click a
          policy to view criteria.
        </p>
      </header>

      <Card>
        <CardHeader title="Ingest a new policy" subtitle="Paste raw text. Claude extracts the criteria." />
        <div className="p-5">
          <PolicyUploader />
        </div>
      </Card>

      {error ? (
        <Card>
          <div className="p-5 text-sm text-red-600">
            Could not reach the API: {error}. Start the backend with `make run`.
          </div>
        </Card>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        {policies.length === 0 ? (
          <Card>
            <div className="p-5 text-sm text-slate-600">
              No policies yet. Use the form above.
            </div>
          </Card>
        ) : (
          policies.map((p) => {
            const required = p.criteria.filter((c) => c.type === "required").length;
            const contra = p.criteria.filter((c) => c.type === "contraindication").length;
            const docs = p.criteria.filter((c) => c.type === "documentation").length;
            return (
              <Card key={p.id}>
                <CardHeader
                  title={
                    <Link href={`/policies?selected=${p.id}`} className="hover:underline">
                      {p.procedure_name}
                    </Link>
                  }
                  subtitle={`${p.payer} | CPT ${p.procedure_code} | effective ${p.effective_date}`}
                  right={
                    <div className="flex gap-1">
                      <Badge tone="info">{required} req</Badge>
                      <Badge tone="denied">{contra} contra</Badge>
                      <Badge tone="neutral">{docs} docs</Badge>
                    </div>
                  }
                />
                <div className="px-5 py-3 text-xs text-slate-500">
                  Policy id: <span className="font-mono">{p.id}</span>
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
