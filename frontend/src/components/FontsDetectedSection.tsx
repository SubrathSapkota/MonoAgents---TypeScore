import { useMemo, useState } from "react";
import type { PageResult } from "../api/types";

interface FontEntry {
  name: string;
  pages: string[];
}

function buildFontEntries(pages: PageResult[]): FontEntry[] {
  const map = new Map<string, Set<string>>();

  for (const page of pages) {
    if (page.error) continue;
    const path = page.path || "/";
    for (const font of page.fonts) {
      if (!map.has(font)) map.set(font, new Set());
      map.get(font)!.add(path);
    }
  }

  return [...map.entries()]
    .map(([name, pageSet]) => ({
      name,
      pages: [...pageSet].sort((a, b) => a.localeCompare(b)),
    }))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
}

function PageBlock({ page }: { page: PageResult }) {
  const [expanded, setExpanded] = useState(false);
  const path = page.path || "/";
  const count = page.fonts.length;

  return (
    <div className={`fonts-detected-page-block${expanded ? " fonts-detected-page-block--open" : ""}`}>
      <button
        className="fonts-detected-page-header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <code className="fonts-detected-page-path" title={path}>{path}</code>
        <div className="fonts-detected-page-header-right">
          <span className="fonts-detected-badge">
            {count} font{count !== 1 ? "s" : ""}
          </span>
          <span className={`fonts-page-chevron${expanded ? " fonts-page-chevron--open" : ""}`} aria-hidden="true">
            ▸
          </span>
        </div>
      </button>
      {expanded && (
        <div className="fonts-detected-page-body">
          {count > 0 ? (
            <div className="fonts-detected-page-fonts" role="list">
              {page.fonts.map((font, index) => (
                <div
                  key={`${path}-${font}-${index}`}
                  className="fonts-detected-page-font-row"
                  role="listitem"
                  title={font}
                >
                  {font}
                </div>
              ))}
            </div>
          ) : (
            <p className="font-none">No fonts detected</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function FontsDetectedSection({ pages }: { pages: PageResult[] }) {
  const entries = useMemo(() => buildFontEntries(pages), [pages]);
  const [search, setSearch] = useState("");
  const validPages = pages.filter((p) => !p.error);
  const errorPages = pages.filter((p) => p.error);

  const filteredEntries = search.trim()
    ? entries.filter((e) => e.name.toLowerCase().includes(search.trim().toLowerCase()))
    : entries;

  if (entries.length === 0 && errorPages.length === 0) {
    return (
      <div className="fonts-detected-empty">
        <p>No fonts detected on the scanned pages.</p>
      </div>
    );
  }

  return (
    <div className="fonts-detected">
      <div className="fonts-detected-summary">
        <span className="fonts-detected-stat">
          <strong>{entries.length}</strong> unique font{entries.length !== 1 ? "s" : ""}
        </span>
        <span className="fonts-detected-stat-sep">·</span>
        <span className="fonts-detected-stat">
          <strong>{validPages.length}</strong> page{validPages.length !== 1 ? "s" : ""} scanned
        </span>
      </div>

      {entries.length > 0 && (
        <div className="fonts-detected-table-section">
          {entries.length > 10 && (
            <div className="fonts-detected-search-wrap">
              <input
                className="fonts-detected-search"
                type="search"
                placeholder="Filter fonts…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <span className="fonts-detected-search-count">
                  {filteredEntries.length} of {entries.length}
                </span>
              )}
            </div>
          )}
          <div className="fonts-detected-table-wrap">
            <table className="fonts-detected-table">
              <thead>
                <tr>
                  <th>Font</th>
                  <th>Pages</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.length > 0 ? (
                  filteredEntries.map((entry) => (
                    <tr key={entry.name}>
                      <td className="fonts-detected-name" title={entry.name}>
                        {entry.name}
                      </td>
                      <td className="fonts-detected-pages-cell">
                        <div className="fonts-detected-paths">
                          {entry.pages.map((path) => (
                            <code key={path} className="fonts-detected-path">
                              {path}
                            </code>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={2} className="fonts-detected-no-match">
                      No fonts match &ldquo;{search}&rdquo;
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {validPages.length > 0 && (
        <div className="fonts-detected-by-page">
          <div className="fonts-detected-by-page-title-row">
            <h3 className="fonts-detected-by-page-title">By page</h3>
            <span className="fonts-detected-by-page-hint">Click a page to expand</span>
          </div>
          <div className="fonts-detected-page-list">
            {validPages.map((page, i) => (
              <PageBlock key={i} page={page} />
            ))}
          </div>
        </div>
      )}

      {errorPages.length > 0 && (
        <div className="fonts-detected-errors">
          {errorPages.map((page, i) => (
            <p key={i} className="font-error">
              {page.path || "/"}: {page.error}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
