import { useEffect, useRef, useState } from "react";
import { historyApi } from "../api/client";
import type { ScanSummary, ScanDetail } from "../api/types";
import IssuesAccordion from "../components/IssuesAccordion";
import { ScoreRing, scoreColor } from "../components/ScoreRing";

const PAGE_SIZE = 10;

const METRIC_LABELS: Record<string, string> = {
  brand_consistency: "Brand",
  license_compliance: "License",
  performance: "Perf",
  accessibility: "A11y",
  developer_experience: "DevEx",
};

function MiniScore({ label, value }: { label: string; value?: number }) {
  if (value === undefined || value === null) return null;
  return (
    <div className="mini-score">
      <span className="mini-score-val" style={{ color: scoreColor(value) }}>
        {Math.round(value)}
      </span>
      <span className="mini-score-label">{label}</span>
    </div>
  );
}

function HistoryRow({
  scan,
  onExpand,
  isExpanded,
}: {
  scan: ScanSummary;
  onExpand: () => void;
  isExpanded: boolean;
}) {
  return (
    <div className={`history-row ${isExpanded ? "history-row--expanded" : ""}`}>
      <div className="history-row-main" onClick={onExpand}>
        <div className="history-row-left">
          <div
            className="history-row-score"
            style={{
              color: scan.overall_score ? scoreColor(scan.overall_score) : "#999",
            }}
          >
            {scan.overall_score ?? "—"}
          </div>
          <div>
            <p className="history-row-url">{scan.url}</p>
            <p className="history-row-date">
              {new Date(scan.created_at).toLocaleString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
              {scan.issues_count > 0 && (
                <span className="history-row-issues">
                  {" "}· {scan.issues_count} issue{scan.issues_count !== 1 ? "s" : ""}
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="history-row-scores">
          {Object.entries(scan.scores).map(([key, val]) => (
            <MiniScore key={key} label={METRIC_LABELS[key] ?? key} value={val ?? undefined} />
          ))}
        </div>
        <span className="history-row-chevron">{isExpanded ? "▲" : "▼"}</span>
      </div>
    </div>
  );
}

function ExpandedDetail({ scanId }: { scanId: number }) {
  const [detail, setDetail] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    historyApi
      .get(scanId)
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [scanId]);

  if (loading) return <div className="history-detail-loading"><div className="spinner spinner-sm" /></div>;
  if (!detail) return null;

  return (
    <div className="history-detail">
      <div className="history-detail-body">
        <div className="history-detail-ring">
          <ScoreRing score={detail.overall_score ?? 0} size={100} />
        </div>
        <div className="history-detail-issues">
          <IssuesAccordion issues={detail.issues} variant="embedded" />
        </div>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    setLoading(true);
    setError(null);
    setExpandedId(null);

    historyApi
      .list(PAGE_SIZE, (page - 1) * PAGE_SIZE)
      .then((data) => {
        setScans(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => {
    if (!loading && listRef.current) {
      listRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [page, loading]);

  function toggleExpand(id: number) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  function goToPage(nextPage: number) {
    if (nextPage < 1 || nextPage > totalPages || nextPage === page) return;
    setPage(nextPage);
  }

  if (loading && scans.length === 0) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  const rangeStart = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Scan History</h1>
          <p className="page-subtitle">
            {total} analysis{total !== 1 ? "es" : ""} recorded
            {total > 0 && (
              <span className="history-page-range">
                {" "}· showing {rangeStart}–{rangeEnd}
              </span>
            )}
          </p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {total === 0 && !error ? (
        <div className="empty-state">
          <div className="empty-icon">⊡</div>
          <h3>No scans yet</h3>
          <p>Run your first website analysis from the Analyze page.</p>
        </div>
      ) : (
        <>
          <div className="history-list" ref={listRef}>
            {loading ? (
              <div className="history-list-loading">
                <div className="spinner spinner-sm" />
              </div>
            ) : (
              scans.map((scan) => (
                <div key={scan.id} className="history-entry">
                  <HistoryRow
                    scan={scan}
                    onExpand={() => toggleExpand(scan.id)}
                    isExpanded={expandedId === scan.id}
                  />
                  {expandedId === scan.id && <ExpandedDetail scanId={scan.id} />}
                </div>
              ))
            )}
          </div>

          {totalPages > 1 && (
            <nav className="history-pagination" aria-label="Scan history pages">
              <div className="history-pagination-inner">
                <button
                  type="button"
                  className="history-page-nav"
                  onClick={() => goToPage(page - 1)}
                  disabled={page <= 1 || loading}
                  aria-label="Previous page"
                >
                  <span className="history-page-nav-icon" aria-hidden="true">‹</span>
                  <span>Prev</span>
                </button>
                <div className="history-page-indicator">
                  <span className="history-page-current">{page}</span>
                  <span className="history-page-sep">of</span>
                  <span className="history-page-total">{totalPages}</span>
                </div>
                <button
                  type="button"
                  className="history-page-nav"
                  onClick={() => goToPage(page + 1)}
                  disabled={page >= totalPages || loading}
                  aria-label="Next page"
                >
                  <span>Next</span>
                  <span className="history-page-nav-icon" aria-hidden="true">›</span>
                </button>
              </div>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
