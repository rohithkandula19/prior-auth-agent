import type { EvalSummary } from "@/lib/types";

const W = 460;
const H = 260;
const PAD = { top: 16, right: 16, bottom: 36, left: 44 };
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

  // Diagonal reference line
  const ref = `M ${PAD.left} ${PAD.top + PH} L ${PAD.left + PW} ${PAD.top}`;

  // Gridlines at 0.25, 0.5, 0.75
  const grid = [0.25, 0.5, 0.75];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-[260px] w-full"
      role="img"
      aria-label="Calibration curve"
    >
      {/* Subtle grid */}
      {grid.map((g) => (
        <g key={`gx-${g}`}>
          <line
            x1={PAD.left + g * PW}
            y1={PAD.top}
            x2={PAD.left + g * PW}
            y2={PAD.top + PH}
            stroke="#eee9dc"
            strokeWidth={1}
          />
          <line
            x1={PAD.left}
            y1={PAD.top + (1 - g) * PH}
            x2={PAD.left + PW}
            y2={PAD.top + (1 - g) * PH}
            stroke="#eee9dc"
            strokeWidth={1}
          />
        </g>
      ))}

      {/* Frame */}
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + PH} stroke="#d8d2c1" />
      <line
        x1={PAD.left}
        y1={PAD.top + PH}
        x2={PAD.left + PW}
        y2={PAD.top + PH}
        stroke="#d8d2c1"
      />

      {/* Reference diagonal */}
      <path d={ref} stroke="#bdb6a3" strokeDasharray="4 4" fill="none" />

      {/* Curve */}
      {points.length > 1 ? (
        <path d={path} stroke="#111" strokeWidth={1.75} fill="none" />
      ) : null}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={5} fill="#fbfaf6" stroke="#111" strokeWidth={1.5} />
        </g>
      ))}

      {/* Axis labels */}
      <text
        x={PAD.left + PW / 2}
        y={H - 10}
        textAnchor="middle"
        fontSize="11"
        fill="#8a8472"
      >
        Predicted confidence
      </text>
      <text
        x={14}
        y={PAD.top + PH / 2}
        textAnchor="middle"
        fontSize="11"
        fill="#8a8472"
        transform={`rotate(-90 14 ${PAD.top + PH / 2})`}
      >
        Observed accuracy
      </text>
      {/* Axis ticks */}
      {[0, 0.5, 1].map((t) => (
        <text
          key={`xt-${t}`}
          x={PAD.left + t * PW}
          y={PAD.top + PH + 16}
          textAnchor="middle"
          fontSize="10"
          fill="#8a8472"
        >
          {t}
        </text>
      ))}
      {[0, 0.5, 1].map((t) => (
        <text
          key={`yt-${t}`}
          x={PAD.left - 8}
          y={PAD.top + (1 - t) * PH + 3}
          textAnchor="end"
          fontSize="10"
          fill="#8a8472"
        >
          {t}
        </text>
      ))}
    </svg>
  );
}
