import { api } from "@/lib/api";
import { DetermineForm } from "@/components/DetermineForm";

export const dynamic = "force-dynamic";

export default async function DeterminePage() {
  const [policies, patients] = await Promise.all([
    api.listPolicies().catch(() => []),
    api.listPatients().catch(() => []),
  ]);

  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <p className="eyebrow">Run a determination</p>
        <h1 className="h-display text-[44px] tracking-tightest">
          Select a policy and a patient case.
        </h1>
        <p className="max-w-xl text-[15px] leading-relaxed text-body">
          The agent streams progress as it checks each criterion. When it is
          done, you land on the citation viewer with the decision, gaps, and
          supporting evidence.
        </p>
      </header>
      <DetermineForm policies={policies} patients={patients} />
    </div>
  );
}
