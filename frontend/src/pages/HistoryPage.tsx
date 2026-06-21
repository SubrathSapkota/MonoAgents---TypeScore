import { useEffect, useState } from "react";
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

  const [urlSearch, setUrlSearch] = useState("");
  const [debouncedUrl, setDebouncedUrl] = useState("");
  const [minScore, setMinScore] = useState("");
  const [maxScore, setMaxScore] = useState("");

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const parsedMin = minScore === "" ? undefined : Number(minScore);
  const parsedMax = maxScore === "" ? undefined : Number(maxScore);
  const hasScoreError =
    (minScore !== "" && Number.isNaN(parsedMin!)) ||
    (maxScore !== "" && Number.isNaN(parsedMax!)) ||
    (parsedMin != null && parsedMax != null && parsedMin > parsedMax);

  const hasActiveFilters =
    debouncedUrl.length > 0 || minScore !== "" || maxScore !== "";

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedUrl(urlSearch.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [urlSearch]);

  useEffect(() => {
    if (hasScoreError) return;

    setLoading(true);
    setError(null);
    setExpandedId(null);

    historyApi
      .list({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        url: debouncedUrl || undefined,
        min_score: parsedMin,
        max_score: parsedMax,
      })
      .then((data) => {
        setScans(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page, debouncedUrl, minScore, maxScore, hasScoreError]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  function toggleExpand(id: number) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  function goToPage(nextPage: number) {
    if (nextPage < 1 || nextPage > totalPages || nextPage === page) return;
    setPage(nextPage);
  }

  function handleScoreChange(field: "min" | "max", value: string) {
    if (field === "min") setMinScore(value);
    else setMaxScore(value);
    setPage(1);
  }

  function clearFilters() {
    setUrlSearch("");
    setDebouncedUrl("");
    setMinScore("");
    setMaxScore("");
    setPage(1);
  }

  if (loading && scans.length === 0 && !hasActiveFilters) {
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
            {hasActiveFilters ? (
              <>
                {total} match{total !== 1 ? "es" : ""}
                {total > 0 && (
                  <span className="history-page-range">
                    {" "}· showing {rangeStart}–{rangeEnd}
                  </span>
                )}
              </>
            ) : (
              <>
                {total} analysis{total !== 1 ? "es" : ""} recorded
                {total > 0 && (
                  <span className="history-page-range">
                    {" "}· showing {rangeStart}–{rangeEnd}
                  </span>
                )}
              </>
            )}
          </p>
        </div>
      </div>

      <div className="history-filters">
        <div className="history-filters-row">
          <label className="history-filter-field history-filter-field--url">
            <span className="history-filter-label">URL</span>
            <input
              className="history-filter-input"
              type="search"
              placeholder="Search by domain or path…"
              value={urlSearch}
              onChange={(e) => setUrlSearch(e.target.value)}
            />
          </label>
          <label className="history-filter-field history-filter-field--score">
            <span className="history-filter-label">Min score</span>
            <input
              className="history-filter-input"
              type="number"
              min={0}
              max={100}
              step={1}
              placeholder="0"
              value={minScore}
              onChange={(e) => handleScoreChange("min", e.target.value)}
            />
          </label>
          <label className="history-filter-field history-filter-field--score">
            <span className="history-filter-label">Max score</span>
            <input
              className="history-filter-input"
              type="number"
              min={0}
              max={100}
              step={1}
              placeholder="100"
              value={maxScore}
              onChange={(e) => handleScoreChange("max", e.target.value)}
            />
          </label>
          {hasActiveFilters && (
            <button type="button" className="history-filter-clear" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>
        {hasScoreError && (
          <p className="history-filter-error" role="alert">
            Enter valid scores between 0–100, with min ≤ max.
          </p>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {total === 0 && !error && !loading ? (
        <div className="empty-state">
          <div className="empty-icon">⊡</div>
          {hasActiveFilters ? (
            <>
              <h3>No matching scans</h3>
              <p>Try adjusting your filters or search term.</p>
              <button type="button" className="btn btn-secondary" style={{ marginTop: 16 }} onClick={clearFilters}>
                Clear filters
              </button>
            </>
          ) : (
            <>
              <h3>No scans yet</h3>
              <p>Run your first website analysis from the Analyze page.</p>
            </>
          )}
        </div>
      ) : (
        <>
          <div className="history-list">
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
