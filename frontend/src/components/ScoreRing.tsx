export function scoreColor(score: number): string {
  if (score >= 80) return "var(--color-good)";
  if (score >= 50) return "var(--color-warn)";
  return "var(--color-bad)";
}

export function scoreGrade(score: number): string {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 50) return "D";
  return "F";
}

export function ScoreRing({
  score,
  size = 160,
  label,
}: {
  score: number;
  size?: number;
  label?: string;
}) {
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;

  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={scoreColor(score)}
          strokeWidth={stroke}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
      </svg>
      <div className="score-ring-inner">
        <span className="score-number" style={{ color: scoreColor(score) }}>
          {score}
        </span>
        {label ? (
          <span className="score-grade" style={{ fontSize: 11 }}>
            {label}
          </span>
        ) : (
          <span className="score-grade">{scoreGrade(score)}</span>
        )}
      </div>
    </div>
  );
}
