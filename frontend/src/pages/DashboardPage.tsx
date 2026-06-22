import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { historyApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { ScanSummary } from "../api/types";
import { ScoreRing, scoreColor } from "../components/ScoreRing";

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

const METRIC_LABELS: Record<string, string> = {
  brand_consistency: "Brand Consistency",
  license_compliance: "License Compliance",
  performance: "Performance",
  accessibility: "Accessibility",
  developer_experience: "Developer Experience",
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    historyApi
      .list({ limit: 5 })
      .then((s) => {
        setScans(s.items);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const avgScore =
    scans.length > 0
      ? Math.round(
          scans.reduce((sum, s) => sum + (s.overall_score ?? 0), 0) / scans.length
        )
      : null;

  const latestScan = scans[0] ?? null;

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page dashboard-page">
      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="dashboard-hero">
        <div className="dashboard-hero-glow dashboard-hero-glow--1" aria-hidden="true" />
        <div className="dashboard-hero-glow dashboard-hero-glow--2" aria-hidden="true" />
        <div className="dashboard-hero-content">
          <p className="dashboard-hero-eyebrow">Font compliance dashboard</p>
          <h1 className="dashboard-hero-title">
            {getGreeting()}, {user?.name?.split(" ")[0]}.
          </h1>
          <p className="dashboard-hero-subtitle">
            Track license coverage, scan results, and font health across your projects — all in one place.
          </p>
          <div className="dashboard-hero-actions">
            <Link to="/analyze" className="btn btn-primary">
              Run Analysis
            </Link>
            <Link to="/history" className="btn btn-secondary">
              View History
            </Link>
          </div>
        </div>
        {avgScore !== null && (
          <div className="dashboard-hero-score">
            <ScoreRing score={avgScore} size={100} />
            <span className="dashboard-hero-score-label">Avg. score</span>
          </div>
        )}
      </section>

      {/* ── Stat cards ──────────────────────────────────────── */}
      <div className="stat-grid">
        <div className="stat-card stat-card--violet">
          <div className="stat-card-top">
            <span className="stat-label">Scans Run</span>
            <span className="stat-icon">⟳</span>
          </div>
          <span className="stat-value">
            {scans.length > 4 ? "5+" : scans.length}
          </span>
          <span className="stat-meta">recent analyses</span>
        </div>

        <div className="stat-card stat-card--emerald">
          <div className="stat-card-top">
            <span className="stat-label">Avg. TypeScore</span>
            <span className="stat-icon">◈</span>
          </div>
          <span
            className="stat-value"
            style={{ color: avgScore ? scoreColor(avgScore) : undefined }}
          >
            {avgScore ?? "—"}
          </span>
          <span className="stat-meta">
            {scans.length ? "across all scans" : "no scans yet"}
          </span>
        </div>

        <div className="stat-card stat-card--amber">
          <div className="stat-card-top">
            <span className="stat-label">Issues Found</span>
            <span className="stat-icon">⚠</span>
          </div>
          <span className="stat-value">
            {scans.reduce((sum, s) => sum + s.issues_count, 0)}
          </span>
          <span className="stat-meta">across recent scans</span>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* ── Latest scan ─────────────────────────────────── */}
        <div className="dash-card dash-card--large">
          <div className="dash-card-header">
            <h2 className="dash-card-title">Latest Scan</h2>
            {latestScan && (
              <Link to="/history" className="dash-card-link">
                View all
              </Link>
            )}
          </div>

          {latestScan ? (
            <div className="latest-scan">
              <div className="latest-scan-meta">
                <p className="latest-scan-url">{latestScan.url}</p>
                <p className="latest-scan-date">
                  {new Date(latestScan.created_at).toLocaleDateString("en-US", {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                </p>
              </div>
              <div className="latest-scan-body">
                <ScoreRing score={latestScan.overall_score ?? 0} size={120} />
                <div className="latest-scan-breakdown">
                  {Object.entries(latestScan.scores).map(([key, val]) =>
                    val !== null && val !== undefined ? (
                      <div key={key} className="mini-metric">
                        <span className="mini-metric-label">
                          {METRIC_LABELS[key] ?? key}
                        </span>
                        <div className="mini-bar-track">
                          <div
                            className="mini-bar-fill"
                            style={{
                              width: `${val}%`,
                              backgroundColor: scoreColor(val),
                            }}
                          />
                        </div>
                        <span
                          className="mini-metric-val"
                          style={{ color: scoreColor(val) }}
                        >
                          {val}
                        </span>
                      </div>
                    ) : null
                  )}
                </div>
              </div>
              {latestScan.issues_count > 0 && (
                <p className="latest-scan-issues">
                  {latestScan.issues_count} issue
                  {latestScan.issues_count !== 1 ? "s" : ""} found
                </p>
              )}
            </div>
          ) : (
            <div className="dash-empty">
              <div className="dash-empty-icon">◈</div>
              <p>No scans yet.</p>
              <p className="dash-empty-hint">
                Analyze a URL to get your first TypeScore breakdown.
              </p>
              <Link to="/analyze" className="btn btn-primary" style={{ marginTop: 16 }}>
                Run your first analysis
              </Link>
            </div>
          )}
        </div>

        {/* ── Quick actions ────────────────────────────────── */}
        <div className="dash-card">
          <div className="dash-card-header">
            <h2 className="dash-card-title">Quick Actions</h2>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Link to="/analyze" className="btn btn-primary btn-full">
              Analyze a Website
            </Link>
            <Link to="/history" className="btn btn-secondary btn-full">
              Browse Scan History
            </Link>
          </div>
        </div>
      </div>

      {/* ── Recent scans table ──────────────────────────────── */}
      {scans.length > 1 && (
        <div className="dash-card dashboard-recent">
          <div className="dash-card-header">
            <h2 className="dash-card-title">Recent Analyses</h2>
            <Link to="/history" className="dash-card-link">
              Full history
            </Link>
          </div>
          <table className="history-table">
            <thead>
              <tr>
                <th>URL</th>
                <th>TypeScore</th>
                <th>Issues</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((s) => (
                <tr key={s.id}>
                  <td className="history-url">{s.url}</td>
                  <td>
                    <span
                      className="history-score"
                      style={{
                        color: s.overall_score ? scoreColor(s.overall_score) : undefined,
                      }}
                    >
                      {s.overall_score ?? "—"}
                    </span>
                  </td>
                  <td>{s.issues_count}</td>
                  <td className="history-date">
                    {new Date(s.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
