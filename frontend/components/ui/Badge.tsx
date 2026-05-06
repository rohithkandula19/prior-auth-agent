import { ReactNode } from "react";

type Tone = "neutral" | "approved" | "denied" | "pending" | "info";

const TONE: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700",
  approved: "bg-emerald-100 text-emerald-800",
  denied: "bg-red-100 text-red-800",
  pending: "bg-amber-100 text-amber-800",
  info: "bg-blue-100 text-blue-800",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${TONE[tone]}`}
    >
      {children}
    </span>
  );
}
