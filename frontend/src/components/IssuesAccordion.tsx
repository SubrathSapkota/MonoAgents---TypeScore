import { useState } from "react";

export const METRIC_LABELS: Record<string, string> = {
  brand_consistency: "Brand Consistency",
  license_compliance: "License Compliance",
  performance: "Performance",
  accessibility: "Accessibility",
  developer_experience: "Developer Experience",
};

export const METRIC_ICONS: Record<string, string> = {
  brand_consistency: "◈",
  license_compliance: "✓",
  performance: "⚡",
  accessibility: "♿",
  developer_experience: "⌘",
};

const METRIC_ORDER = [
  "brand_consistency",
  "license_compliance",
  "performance",
  "accessibility",
  "developer_experience",
];

export interface IssueEntry {
  metric: string;
  message: string;
}

function groupIssues(issues: IssueEntry[]) {
  const map = new Map<string, string[]>();

  for (const issue of issues) {
    if (!map.has(issue.metric)) map.set(issue.metric, []);
    map.get(issue.metric)!.push(issue.message);
  }

  return [...map.entries()]
    .map(([key, violations]) => ({ key, violations }))
    .sort((a, b) => {
      const ai = METRIC_ORDER.indexOf(a.key);
      const bi = METRIC_ORDER.indexOf(b.key);
      if (ai === -1 && bi === -1) return a.key.localeCompare(b.key);
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key.replace(/_/g, " ");
}

export default function IssuesAccordion({
  issues,
  title = "Issues Found",
  variant = "card",
}: {
  issues: IssueEntry[];
  title?: string;
  variant?: "card" | "embedded";
}) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const grouped = groupIssues(issues);

  if (grouped.length === 0) {
    return variant === "embedded" ? (
      <p className="metric-no-issues">✓ No issues recorded</p>
    ) : null;
  }

  const totalIssues = issues.length;

  function toggle(key: string) {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const content = (
    <>
      <div className="issues-banner-header">
        <h2 className="dash-card-title issues-accordion-title">{title}</h2>
        <span className="issues-total-badge">
          {totalIssues} issue{totalIssues !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="issues-accordion">
        {grouped.map(({ key, violations }) => {
          const icon = METRIC_ICONS[key] ?? "•";
          const isOpen = openSections[key] ?? false;
          return (
            <div key={key} className={`issues-section${isOpen ? " issues-section--open" : ""}`}>
              <button
                className="issues-section-header"
                onClick={() => toggle(key)}
                aria-expanded={isOpen}
                type="button"
              >
                <div className="issues-section-left">
                  <span className="issues-section-icon" aria-hidden="true">{icon}</span>
                  <span className="issues-section-label">{metricLabel(key)}</span>
                  <span className="issues-count-badge">{violations.length}</span>
                </div>
                <span
                  className={`issues-chevron${isOpen ? " issues-chevron--open" : ""}`}
                  aria-hidden="true"
                >
                  ▸
                </span>
              </button>
              {isOpen && (
                <div className="issues-section-body">
                  <ul className="issues-section-list">
                    {violations.map((message, i) => (
                      <li key={i} className="issues-section-item">
                        <span className="issues-section-bullet" aria-hidden="true">—</span>
                        <span className="issue-message">{message}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );

  if (variant === "embedded") {
    return <div className="issues-accordion-embedded">{content}</div>;
  }

  return (
    <div className="dash-card" style={{ marginTop: 24 }}>
      {content}
    </div>
  );
}
