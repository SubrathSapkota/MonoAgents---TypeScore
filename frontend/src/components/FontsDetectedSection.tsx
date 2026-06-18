import { useMemo } from "react";
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

export default function FontsDetectedSection({ pages }: { pages: PageResult[] }) {
  const entries = useMemo(() => buildFontEntries(pages), [pages]);
  const validPages = pages.filter((p) => !p.error);
  const errorPages = pages.filter((p) => p.error);

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
        <div className="fonts-detected-table-wrap">
          <table className="fonts-detected-table">
            <thead>
              <tr>
                <th>Font</th>
                <th>Pages</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
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
              ))}
            </tbody>
          </table>
        </div>
      )}

      {validPages.length > 0 && (
        <div className="fonts-detected-by-page">
          <h3 className="fonts-detected-by-page-title">By page</h3>
          <div className="fonts-detected-page-list">
            {validPages.map((page, i) => (
              <div key={i} className="fonts-detected-page-block">
                <div className="fonts-detected-page-header">
                  <code className="fonts-detected-page-path">{page.path || "/"}</code>
                  <span className="fonts-detected-badge">
                    {page.fonts.length} font{page.fonts.length !== 1 ? "s" : ""}
                  </span>
                </div>
                {page.fonts.length > 0 ? (
                  <ul className="fonts-detected-page-fonts">
                    {page.fonts.map((font) => (
                      <li key={font} title={font}>
                        {font}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="font-none">No fonts detected</p>
                )}
              </div>
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
