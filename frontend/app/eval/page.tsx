import { api } from "@/lib/api";
import { EvalDashboard } from "@/components/EvalDashboard";
import type { EvalSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function EvalPage() {
  const initial: EvalSummary = await api.metrics().catch(() => ({
    n: 0,
    agreement: 0,
  }));
  return <EvalDashboard initial={initial} />;
}
