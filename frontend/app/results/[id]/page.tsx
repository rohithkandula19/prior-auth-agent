import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { CitationViewer } from "@/components/CitationViewer";
import { ConfidenceMeter } from "@/components/ConfidenceMeter";
import { CriteriaChecklist } from "@/components/CriteriaChecklist";

export const dynamic = "force-dynamic";

export default async function ResultsPage({
  params,
}: {
  params: { id: string };
}) {
  let determination, policy, patient;
  try {
    determination = await api.getDetermination(params.id);
    [policy, patient] = await Promise.all([
      api.getPolicy(determination.policy_id),
      api.getPatient(determination.patient_id),
    ]);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title={`Determination ${determination.id}`}
          subtitle={`${policy.payer} | ${policy.procedure_name} | patient ${patient.id}`}
          right={
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Badge tone="neutral">{determination.latency_ms} ms</Badge>
              <Badge tone="neutral">${determination.cost_usd.toFixed(4)}</Badge>
            </div>
          }
        />
        <div className="space-y-3 p-5">
          <ConfidenceMeter
            decision={determination.decision}
            confidence={determination.confidence}
          />
          <p className="text-sm text-slate-700">
            <span className="font-medium">Recommended action: </span>
            {determination.recommended_action}
          </p>
          {determination.gaps.length > 0 ? (
            <div className="rounded-md border border-line bg-amber-50 p-3 text-sm">
              <div className="mb-1 font-medium">Documentation gaps</div>
              <ul className="list-inside list-disc text-slate-700">
                {determination.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </Card>

      <Card>
        <CardHeader title="Citations" subtitle="Click a span to highlight the matching pair." />
        <div className="p-5">
          <CitationViewer
            policy={policy}
            patient={patient}
            evaluations={determination.criterion_evaluations}
          />
        </div>
      </Card>

      <Card>
        <CardHeader title="Criteria checklist" />
        <div className="p-5">
          <CriteriaChecklist
            policy={policy}
            evaluations={determination.criterion_evaluations}
          />
        </div>
      </Card>
    </div>
  );
}
