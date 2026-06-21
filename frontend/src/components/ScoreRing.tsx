import { useEffect, useState } from "react";
import { useCountUp } from "../hooks/useCountUp";

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

function ringStroke(size: number): number {
  return Math.max(4, Math.round(size * 0.055));
}

function scoreTextSize(size: number, stroke: number, scoreText: string): number {
  const inner = size - stroke * 2 - 6;
  const chars = Math.max(scoreText.length, 1);
  const maxByWidth = inner / (chars * 0.58);
  const maxByHeight = size * 0.3;
  return Math.floor(Math.min(maxByWidth, maxByHeight, size * 0.28));
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
  const [ready, setReady] = useState(false);
  const stroke = ringStroke(size);
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const targetOffset = circ - (score / 100) * circ;
  const offset = ready ? targetOffset : circ;
  const animatedScore = useCountUp(score, 1200, 150);
  const grade = label ?? scoreGrade(score);
  const scoreText = String(animatedScore);
  const numberSize = scoreTextSize(size, stroke, scoreText);
  const gradeSize = Math.max(9, Math.round(numberSize * 0.36));

  useEffect(() => {
    setReady(false);
    const id = requestAnimationFrame(() => {
      requestAnimationFrame(() => setReady(true));
    });
    return () => cancelAnimationFrame(id);
  }, [score]);

  return (
    <div
      className={`score-ring${ready ? " score-ring--ready" : ""}`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={stroke}
        />
        <circle
          className="score-ring-progress"
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
        />
      </svg>
      <div className="score-ring-inner">
        <span
          className="score-number"
          style={{ color: scoreColor(score), fontSize: numberSize }}
        >
          {animatedScore}
        </span>
        <span
          className="score-grade"
          style={{ fontSize: label ? Math.max(8, gradeSize - 1) : gradeSize }}
        >
          {grade}
        </span>
      </div>
    </div>
  );
}
