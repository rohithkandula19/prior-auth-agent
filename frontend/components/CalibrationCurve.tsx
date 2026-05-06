import type { EvalSummary } from "@/lib/types";

const W = 380;
const H = 220;
const PAD = { top: 12, right: 12, bottom: 28, left: 36 };
const PW = W - PAD.left - PAD.right;
const PH = H - PAD.top - PAD.bottom;

function toXY(conf: number, acc: number) {
  return {
    x: PAD.left + conf * PW,
    y: PAD.top + (1 - acc) * PH,
  };
}

export function CalibrationCurve({
  reliability,
}: {
  reliability: NonNullable<EvalSummary["reliability"]>;
}) {
  const points = (reliability ?? [])
    .filter((r) => r.count > 0)
    .map((r) => toXY(r.avg_confidence, r.accuracy));

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  // Diagonal reference line (perfectly calibrated)
  const ref = `M ${PAD.left} ${PAD.top + PH} L ${PAD.left + PW} ${PAD.top}`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-[220px] w-full"
      role="img"
      aria-label="Calibration curve"
    >
      {/* Frame */}
      <line
        x1={PAD.left}
        y1={PAD.top}
        x2={PAD.left}
        y2={PAD.top + PH}
        stroke="#cbd5e1"
        strokeWidth={1}
      />
      <line
        x1={PAD.left}
        y1={PAD.top + PH}
        x2={PAD.left + PW}
        y2={PAD.top + PH}
        stroke="#cbd5e1"
        strokeWidth={1}
      />
      {/* Reference diagonal */}
      <path d={ref} stroke="#e2e8f0" strokeDasharray="3 3" fill="none" />
      {/* Curve */}
      {points.length > 1 ? (
        <path d={path} stroke="#0f172a" strokeWidth={2} fill="none" />
      ) : null}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3.5} fill="#0f172a" />
      ))}
      {/* Axis labels */}
      <text
        x={PAD.left + PW / 2}
        y={H - 6}
        textAnchor="middle"
        fontSize="10"
        fill="#94a3b8"
      >
        Predicted confidence
      </text>
      <text
        x={10}
        y={PAD.top + PH / 2}
        textAnchor="middle"
        fontSize="10"
        fill="#94a3b8"
        transform={`rotate(-90 10 ${PAD.top + PH / 2})`}
      >
        Observed accuracy
      </text>
      <text x={PAD.left} y={PAD.top + PH + 14} fontSize="9" fill="#94a3b8">
        0
      </text>
      <text x={PAD.left + PW - 6} y={PAD.top + PH + 14} fontSize="9" fill="#94a3b8">
        1
      </text>
      <text x={PAD.left - 14} y={PAD.top + PH + 3} fontSize="9" fill="#94a3b8">
        0
      </text>
      <text x={PAD.left - 14} y={PAD.top + 6} fontSize="9" fill="#94a3b8">
        1
      </text>
    </svg>
  );
}
