import { api } from "@/lib/api";
import { DetermineForm } from "@/components/DetermineForm";

export const dynamic = "force-dynamic";

export default async function DeterminePage() {
  const [policies, patients] = await Promise.all([
    api.listPolicies().catch(() => []),
    api.listPatients().catch(() => []),
  ]);

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <p className="eyebrow">Run a determination</p>
        <h1 className="text-4xl font-semibold tracking-tight">
          Select a policy and a patient case
        </h1>
      </header>
      <DetermineForm policies={policies} patients={patients} />
    </div>
  );
}
