import { api } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { DetermineForm } from "@/components/DetermineForm";

export const dynamic = "force-dynamic";

export default async function DeterminePage() {
  const [policies, patients] = await Promise.all([
    api.listPolicies().catch(() => []),
    api.listPatients().catch(() => []),
  ]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Run a determination</h1>
        <p className="text-sm text-slate-600">
          Pick a policy and a patient, or paste a FHIR Bundle to ingest a new
          patient first. The agent will check each criterion and route you to
          the citation viewer.
        </p>
      </header>
      <Card>
        <CardHeader title="Inputs" subtitle="Policy and patient" />
        <div className="p-5">
          <DetermineForm policies={policies} patients={patients} />
        </div>
      </Card>
    </div>
  );
}
