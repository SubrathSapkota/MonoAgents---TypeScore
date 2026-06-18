import { useState, type FormEvent } from "react";
import { scanApi } from "../api/client";
import type { AnalysisResult, MetricBreakdown } from "../api/types";
import { ScoreRing, scoreColor } from "../components/ScoreRing";
import AnalyzeLoadingAnimation from "../components/AnalyzeLoadingAnimation";
import { parseWebsiteUrl } from "../utils/url";

const METRIC_LABELS: Record<string, { label: string; max: number }> = {
  brand_consistency: { label: "Brand Consistency", max: 20 },
  license_compliance: { label: "License Compliance", max: 30 },
  performance: { label: "Performance", max: 20 },
  accessibility: { label: "Accessibility", max: 15 },
  developer_experience: { label: "Developer Experience", max: 15 },
};

function MetricCard({ metricKey, data }: { metricKey: string; data: MetricBreakdown }) {
  const [expanded, setExpanded] = useState(false);
  const meta = METRIC_LABELS[metricKey] ?? { label: metricKey, max: 100 };
  const displayScore = Math.round((data.score / 100) * meta.max);

  return (
    <div className="metric-card">
      <div className="metric-header" onClick={() => setExpanded(!expanded)}>
        <div>
          <h3 className="metric-label">{meta.label}</h3>
          <span className="metric-weight">Weight: {(data.weight * 100).toFixed(0)}%</span>
        </div>
        <div className="metric-score-wrap">
          <span className="metric-score" style={{ color: scoreColor(data.score) }}>
            {displayScore}
          </span>
          <span className="metric-score-max">/{meta.max}</span>
        </div>
      </div>
      <div className="metric-bar-track">
        <div
          className="metric-bar-fill"
          style={{ width: `${data.score}%`, backgroundColor: scoreColor(data.score) }}
        />
      </div>
      {expanded && (
        <div className="metric-expand">
          {data.violations.length > 0 ? (
            <ul className="metric-violations">
              {data.violations.map((v, i) => (
                <li key={i}>{v}</li>
              ))}
            </ul>
          ) : (
            <p className="metric-no-issues">✓ No issues found</p>
          )}
        </div>
      )}
    </div>
  );
}

function IssuesBanner({ result }: { result: AnalysisResult }) {
  const allIssues: { metric: string; message: string }[] = [];
  Object.entries(result.scores.breakdown).forEach(([key, data]) => {
    data.violations.forEach((v) => allIssues.push({ metric: key, message: v }));
  });

  if (allIssues.length === 0) return null;

  return (
    <div className="dash-card" style={{ marginTop: 24 }}>
      <h2 className="dash-card-title" style={{ marginBottom: 16 }}>
        Issues Found
      </h2>
      <ul className="issues-list">
        {allIssues.map((issue, i) => (
          <li key={i} className="issue-item">
            <span className="issue-metric">
              {METRIC_LABELS[issue.metric]?.label ?? issue.metric}
            </span>
            <span className="issue-message">{issue.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const SCAN_METRICS = [
  { icon: "◈", label: "Brand consistency" },
  { icon: "✓", label: "License compliance" },
  { icon: "⚡", label: "Performance" },
  { icon: "♿", label: "Accessibility" },
  { icon: "⌘", label: "Developer experience" },
];

export default function AnalyzePage() {
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  function handleUrlChange(value: string) {
    setUrl(value);
    if (urlError) setUrlError(null);
    if (error) setError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    const parsed = parseWebsiteUrl(url);
    if (!parsed.valid) {
      setUrlError(parsed.message);
      return;
    }

    setLoading(true);
    setError(null);
    setUrlError(null);
    setResult(null);

    try {
      const data = await scanApi.analyze(parsed.url);
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page analyze-page">
      <section className="analyze-panel">
        <div className="analyze-panel-glow analyze-panel-glow--1" aria-hidden="true" />
        <div className="analyze-panel-glow analyze-panel-glow--2" aria-hidden="true" />

        <div className="analyze-panel-header">
          <p className="analyze-panel-eyebrow">Website scanner</p>
          <h1 className="analyze-panel-title">Analyze Website</h1>
          <p className="analyze-panel-subtitle">
            Enter a URL to generate a TypeScore across brand consistency, license
            compliance, performance, accessibility, and developer experience.
          </p>
        </div>

        <div className="analyze-metrics">
          {SCAN_METRICS.map((metric) => (
            <span key={metric.label} className="analyze-metric-chip">
              <span className="analyze-metric-icon">{metric.icon}</span>
              {metric.label}
            </span>
          ))}
        </div>

        <form className="analyze-form" onSubmit={handleSubmit} noValidate>
          <div className="analyze-form-fields">
            <div className={`analyze-input-wrap${urlError ? " analyze-input-wrap--error" : ""}`}>
              <span className="analyze-input-icon" aria-hidden="true">
                ⟳
              </span>
              <input
                className="form-input analyze-input"
                type="text"
                inputMode="url"
                autoComplete="url"
                placeholder="https://yourwebsite.com"
                value={url}
                onChange={(e) => handleUrlChange(e.target.value)}
                disabled={loading}
                aria-invalid={urlError ? true : undefined}
                aria-describedby={urlError ? "analyze-url-error" : undefined}
              />
            </div>
            {urlError && (
              <p id="analyze-url-error" className="analyze-field-error" role="alert">
                {urlError}
              </p>
            )}
          </div>
          <button
            className="btn btn-primary analyze-submit"
            type="submit"
            disabled={loading || !url.trim()}
          >
            {loading ? "Scanning…" : "Run Analysis"}
          </button>
        </form>

        <div className="analyze-tip">
          <span className="analyze-tip-icon" aria-hidden="true">
            i
          </span>
          <p>
            Add fonts to your library first — the compliance score checks whether
            your site uses fonts you&apos;ve licensed.
          </p>
        </div>
      </section>

      {/* ── Loading ───────────────────────────────────────── */}
      {loading && <AnalyzeLoadingAnimation />}

      {error && <div className="error-banner analyze-error">{error}</div>}

      {/* ── Results ───────────────────────────────────────── */}
      {result && (
        <div className="analyze-results">
          {/* Overall score */}
          <div className="dash-card overall-card">
            <div className="overall-left">
              <div>
                <h2 className="section-title">TypeScore</h2>
                <p className="overall-url">{result.base_url}</p>
                <p className="overall-pages">
                  {result.pages.length} page{result.pages.length !== 1 ? "s" : ""} scanned
                </p>
                {result.scan_id && (
                  <p className="overall-saved">✓ Saved to history (#{result.scan_id})</p>
                )}
              </div>
            </div>
            <ScoreRing score={result.scores.overall_score} size={140} />
          </div>

          {/* Metric breakdown */}
          <div className="dash-card" style={{ marginTop: 24 }}>
            <h2 className="dash-card-title" style={{ marginBottom: 16 }}>
              Score Breakdown
            </h2>
            <div className="metric-grid">
              {Object.entries(result.scores.breakdown).map(([key, data]) => (
                <MetricCard key={key} metricKey={key} data={data} />
              ))}
            </div>
          </div>

          {/* Issues */}
          <IssuesBanner result={result} />

          {/* Fonts detected */}
          <div className="dash-card" style={{ marginTop: 24 }}>
            <h2 className="dash-card-title" style={{ marginBottom: 16 }}>
              Fonts Detected
            </h2>
            <div className="fonts-grid">
              {result.pages.map((page, i) => (
                <div key={i} className="font-page-card">
                  <h4 className="font-page-path">{page.path || "/"}</h4>
                  {page.error ? (
                    <p className="font-error">{page.error}</p>
                  ) : (
                    <div className="font-tags">
                      {page.fonts.length > 0 ? (
                        page.fonts.map((f, j) => (
                          <span key={j} className="font-tag">{f}</span>
                        ))
                      ) : (
                        <span className="font-none">No fonts detected</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Accessibility violations */}
          {result.accessibility && result.accessibility.violations.length > 0 && (
            <div className="dash-card" style={{ marginTop: 24 }}>
              <h2 className="dash-card-title" style={{ marginBottom: 16 }}>
                Accessibility Violations
              </h2>
              <div className="violations-list">
                {result.accessibility.violations.map((v, i) => (
                  <div key={i} className={`violation-item impact-${v.impact}`}>
                    <div className="violation-header">
                      <span className={`impact-badge ${v.impact}`}>{v.impact}</span>
                      <span className="violation-id">{v.id}</span>
                      <span className="violation-count">
                        {v.count} instance{v.count !== 1 ? "s" : ""}
                      </span>
                    </div>
                    <p className="violation-desc">{v.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Lighthouse metrics */}
          {result.lighthouse && (
            <div className="dash-card" style={{ marginTop: 24 }}>
              <h2 className="dash-card-title" style={{ marginBottom: 16 }}>
                Lighthouse Metrics
              </h2>
              <div className="lh-stats">
                <div className="lh-stat">
                  <span className="lh-value">{result.lighthouse.performance}</span>
                  <span className="lh-label">Performance</span>
                </div>
                <div className="lh-stat">
                  <span className="lh-value">
                    {result.lighthouse.lcp_ms
                      ? `${(result.lighthouse.lcp_ms / 1000).toFixed(1)}s`
                      : "—"}
                  </span>
                  <span className="lh-label">LCP</span>
                </div>
                <div className="lh-stat">
                  <span className="lh-value">{result.lighthouse.cls ?? "—"}</span>
                  <span className="lh-label">CLS</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
