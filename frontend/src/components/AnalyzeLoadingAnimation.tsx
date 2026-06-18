import { useEffect, useState, type CSSProperties } from "react";

const SCAN_STEPS = [
  "Crawling pages",
  "Detecting fonts",
  "Running Lighthouse",
  "Checking accessibility",
  "Calculating TypeScore",
];

const ORBIT_GLYPHS = ["Aa", "Bb", "Gg", "Rr", "Ss", "Tt"];

export default function AnalyzeLoadingAnimation() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStepIndex((current) => (current + 1) % SCAN_STEPS.length);
    }, 2200);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="analyze-scan" role="status" aria-live="polite" aria-busy="true">
      <div className="analyze-scan-visual" aria-hidden="true">
        <div className="analyze-scan-glow analyze-scan-glow--1" />
        <div className="analyze-scan-glow analyze-scan-glow--2" />

        <div className="analyze-scan-orbit">
          {ORBIT_GLYPHS.map((glyph, index) => (
            <span
              key={glyph}
              className="analyze-scan-glyph"
              style={{ "--glyph-index": index } as CSSProperties}
            >
              {glyph}
            </span>
          ))}
        </div>

        <div className="analyze-scan-core">
          <div className="analyze-scan-ring analyze-scan-ring--outer" />
          <div className="analyze-scan-ring analyze-scan-ring--inner" />
          <div className="analyze-scan-beam" />
          <span className="analyze-scan-mark">Ts</span>
        </div>
      </div>

      <div className="analyze-scan-status">
        <p className="analyze-scan-step" key={stepIndex}>
          {SCAN_STEPS[stepIndex]}
          <span className="analyze-scan-dots">
            <span />
            <span />
            <span />
          </span>
        </p>
        <div className="analyze-scan-track">
          <div className="analyze-scan-track-fill" />
        </div>
        <p className="analyze-loading-sub">This may take 1–2 minutes.</p>
      </div>
    </div>
  );
}
