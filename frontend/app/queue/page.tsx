import Link from "next/link";
import { api } from "@/lib/api";
import type { Determination } from "@/lib/types";

export const dynamic = "force-dynamic";

const AUTO_THRESHOLD = 0.85;
const REVIEW_LOWER = 0.5;

type Bucket = "auto" | "review" | "escalate";

function bucket(d: Determination): Bucket {
  if (d.confidence >= AUTO_THRESHOLD) return "auto";
  if (d.confidence >= REVIEW_LOWER) return "review";
  return "escalate";
}

function decisionTone(decision: string): string {
  if (decision === "approved") return "text-approved";
  if (decision === "denied") return "text-denied";
  return "text-pending";
}

export default async function QueuePage() {
  const [determinations, policies, patients] = await Promise.all([
    api.listDeterminations().catch(() => [] as Determination[]),
    api.listPolicies().catch(() => []),
    api.listPatients().catch(() => []),
  ]);

  const policyById = new Map(policies.map((p) => [p.id, p]));
  const patientById = new Map(patients.map((p) => [p.id, p]));

  const auto = determinations.filter((d) => bucket(d) === "auto");
  const review = determinations.filter((d) => bucket(d) === "review");
  const escalate = determinations.filter((d) => bucket(d) === "escalate");

  const Section = ({
    eyebrow,
    title,
    items,
    sla,
  }: {
    eyebrow: string;
    title: string;
    items: Determination[];
    sla: string;
  }) => (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2 className="mt-2 text-[19px] font-medium tracking-tight">{title}</h2>
        </div>
        <p className="text-xs text-soft">{sla}</p>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-soft">No items in this bucket.</p>
      ) : (
        <ul className="divide-y divide-rule">
          {items.map((d) => {
            const policy = policyById.get(d.policy_id);
            const patient = patientById.get(d.patient_id);
            const detIdShort = d.id.toUpperCase().replace(/^DET_?/, "DET-");
            return (
              <li key={d.id}>
                <Link
                  href={`/results/${d.id}`}
                  className="flex items-baseline justify-between gap-6 py-4 hover:bg-canvas"
                >
                  <div className="min-w-0">
                    <p className="text-[15px] font-medium text-ink">
                      {policy?.procedure_name ?? d.policy_id}
                      <span className="text-rule"> · </span>
                      <span className="text-soft">{patient?.id ?? d.patient_id}</span>
                    </p>
                    <p className="mt-0.5 font-mono text-xs text-soft">{detIdShort}</p>
                  </div>
                  <div className="flex items-baseline gap-6 text-sm">
                    <span className={decisionTone(d.decision)}>
                      {d.decision.replace(/_/g, " ")}
                    </span>
                    <span className="font-mono text-xs text-soft">
                      {d.confidence.toFixed(2)}
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );

  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <p className="eyebrow">Adjudication queue</p>
        <h1 className="h-display text-[44px] tracking-tightest">
          Triage by confidence, not by submission order.
        </h1>
        <p className="max-w-xl text-[15px] leading-relaxed text-body">
          Determinations bucket into three lanes. Reviewers spend their time
          where the model was unsure, not on the cases it already handled
          cleanly.
        </p>
      </header>

      <div className="grid gap-12 border-y border-rule py-8 md:grid-cols-3">
        <SummaryStat label="Auto-clear" value={auto.length} hint={`≥ ${AUTO_THRESHOLD}`} />
        <SummaryStat
          label="Reviewer queue"
          value={review.length}
          hint={`${REVIEW_LOWER} - ${AUTO_THRESHOLD}`}
        />
        <SummaryStat label="Escalate" value={escalate.length} hint={`< ${REVIEW_LOWER}`} />
      </div>

      <Section
        eyebrow="Lane 1"
        title={`Auto-clear (confidence ≥ ${AUTO_THRESHOLD})`}
        items={auto}
        sla="Issue letter within 1 business hour"
      />
      <Section
        eyebrow="Lane 2"
        title="Reviewer queue"
        items={review}
        sla="Human reviewer SLA: 4 hours"
      />
      <Section
        eyebrow="Lane 3"
        title="Escalate to medical director"
        items={escalate}
        sla="Medical director SLA: 24 hours"
      />
    </div>
  );
}

function SummaryStat({
  label,
  value,
  hint,
}: {
  label: string;
  value: number;
  hint?: string;
}) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className="mt-3 h-display text-[44px] tracking-tightest">{value}</p>
      {hint ? <p className="mt-1 text-xs text-soft">Confidence {hint}</p> : null}
    </div>
  );
}
