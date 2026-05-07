import { api } from "@/lib/api";
import { PrecheckForm } from "@/components/PrecheckForm";

export const dynamic = "force-dynamic";

export default async function PrecheckPage() {
  const policies = await api.listPolicies().catch(() => []);
  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <p className="eyebrow">Pre-submission check</p>
        <h1 className="h-display text-[44px] tracking-tightest">
          Will this PA clear before you submit it?
        </h1>
        <p className="max-w-xl text-[15px] leading-relaxed text-body">
          Paste your draft note. The agent runs against the chosen policy and
          tells you exactly what to add or document before the prior auth
          packet leaves the office.
        </p>
      </header>
      <PrecheckForm policies={policies} />
    </div>
  );
}
