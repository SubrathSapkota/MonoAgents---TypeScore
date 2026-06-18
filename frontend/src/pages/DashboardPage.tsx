import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { userFontsApi, historyApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { UserFont, ScanSummary } from "../api/types";
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
  const [fonts, setFonts] = useState<UserFont[]>([]);
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      userFontsApi.list().catch(() => [] as UserFont[]),
      historyApi.list(5).catch(() => [] as ScanSummary[]),
    ]).then(([f, s]) => {
      setFonts(f);
      setScans(s);
      setLoading(false);
    });
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
    <div className="page">
      {/* ── Page header ─────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            {getGreeting()}, {user?.name?.split(" ")[0]}.
          </h1>
          <p className="page-subtitle">Here's your font compliance overview.</p>
        </div>
        <Link to="/analyze" className="btn btn-primary">
          Run Analysis
        </Link>
      </div>

      {/* ── Stat cards ──────────────────────────────────────── */}
      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-label">Fonts in Library</span>
          <span className="stat-value">{fonts.length}</span>
          <span className="stat-meta">
            {fonts.filter((f) => f.has_license_data).length} with license data
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Scans Run</span>
          <span className="stat-value">{scans.length > 4 ? "5+" : scans.length}</span>
          <span className="stat-meta">recent analyses</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Avg. TypeScore</span>
          <span
            className="stat-value"
            style={{ color: avgScore ? scoreColor(avgScore) : undefined }}
          >
            {avgScore ?? "—"}
          </span>
          <span className="stat-meta">
            {avgScore ? "across all scans" : "no scans yet"}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">License Coverage</span>
          <span className="stat-value">
            {fonts.length
              ? Math.round(
                  (fonts.filter((f) => f.license_type).length / fonts.length) * 100
                ) + "%"
              : "—"}
          </span>
          <span className="stat-meta">fonts with assigned license</span>
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
              <p>No scans yet.</p>
              <Link to="/analyze" className="btn btn-primary" style={{ marginTop: 12 }}>
                Run your first analysis
              </Link>
            </div>
          )}
        </div>

        {/* ── Font library preview ─────────────────────────── */}
        <div className="dash-card">
          <div className="dash-card-header">
            <h2 className="dash-card-title">My Fonts</h2>
            <Link to="/library" className="dash-card-link">
              Manage library
            </Link>
          </div>

          {fonts.length > 0 ? (
            <ul className="font-preview-list">
              {fonts.slice(0, 6).map((f) => (
                <li key={f.id} className="font-preview-item">
                  <div className="font-preview-name">{f.font_name}</div>
                  <div className="font-preview-meta">
                    {f.category && (
                      <span className="badge badge-cat">{f.category}</span>
                    )}
                    {f.license_type && (
                      <span className="badge badge-lic">{f.license_type}</span>
                    )}
                    {!f.has_license_data && (
                      <span className="badge badge-warn">No license data</span>
                    )}
                  </div>
                </li>
              ))}
              {fonts.length > 6 && (
                <li className="font-preview-more">
                  +{fonts.length - 6} more fonts
                </li>
              )}
            </ul>
          ) : (
            <div className="dash-empty">
              <p>No fonts in your library.</p>
              <Link to="/library" className="btn btn-secondary" style={{ marginTop: 12 }}>
                Add fonts
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* ── Recent scans table ──────────────────────────────── */}
      {scans.length > 1 && (
        <div className="dash-card" style={{ marginTop: 24 }}>
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
