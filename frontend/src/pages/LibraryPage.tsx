import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { userFontsApi, fontsApi } from "../api/client";
import type { UserFont, FontSummary } from "../api/types";

const LICENSE_OPTIONS = [
  { value: "", label: "Choose license type (optional)" },
  { value: "desktop", label: "Desktop" },
  { value: "webfont", label: "Webfont" },
  { value: "app", label: "App" },
  { value: "edoc", label: "Electronic Doc" },
  { value: "digital_ad", label: "Digital Ad" },
];

const CATEGORY_COLORS: Record<string, string> = {
  "serif": "#7c3aed",
  "sans-serif": "#0891b2",
  "display": "#be185d",
  "monospace": "#059669",
  "script": "#d97706",
};

function SourceBadge({ source }: { source: string }) {
  const labels: Record<string, string> = {
    catalog: "Catalog",
    upload: "Uploaded",
    manual: "Manual",
  };
  return (
    <span className={`badge badge-source badge-source--${source}`}>
      {labels[source] ?? source}
    </span>
  );
}

export default function LibraryPage() {
  const navigate = useNavigate();
  const [fonts, setFonts] = useState<UserFont[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add font modal
  const [showAdd, setShowAdd] = useState(false);
  const [addTab, setAddTab] = useState<"manual" | "catalog">("manual");
  const [addName, setAddName] = useState("");
  const [addLicense, setAddLicense] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Catalog search
  const [catalogFonts, setCatalogFonts] = useState<FontSummary[]>([]);
  const [catalogSearch, setCatalogSearch] = useState("");

  // Folder upload
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [uploadLicense, setUploadLicense] = useState("");
  const [uploadResult, setUploadResult] = useState<{ added: string[]; skipped: string[] } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await userFontsApi.list();
      setFonts(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (addTab === "catalog") {
      fontsApi.list(catalogSearch || undefined).then(setCatalogFonts).catch(() => {});
    }
  }, [addTab, catalogSearch]);

  async function handleAddManual() {
    if (!addName.trim()) return;
    setAddLoading(true);
    setAddError(null);
    try {
      await userFontsApi.add({ font_name: addName.trim(), license_type: addLicense || undefined });
      setAddName("");
      setAddLicense("");
      setShowAdd(false);
      load();
    } catch (err: unknown) {
      setAddError(err instanceof Error ? err.message : "Failed to add");
    } finally {
      setAddLoading(false);
    }
  }

  async function handleAddFromCatalog(fontId: number) {
    setAddLoading(true);
    setAddError(null);
    try {
      await userFontsApi.add({ font_id: fontId, license_type: addLicense || undefined });
      setShowAdd(false);
      load();
    } catch (err: unknown) {
      setAddError(err instanceof Error ? err.message : "Failed to add");
    } finally {
      setAddLoading(false);
    }
  }

  async function handleFolderUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setAddLoading(true);
    setAddError(null);
    try {
      const res = await userFontsApi.uploadFolder(files, uploadLicense || undefined);
      setUploadResult({ added: res.added, skipped: res.skipped });
      load();
    } catch (err: unknown) {
      setAddError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setAddLoading(false);
      if (e.target) e.target.value = "";
    }
  }

  async function handleRemove(id: number) {
    if (!confirm("Remove this font from your library?")) return;
    try {
      await userFontsApi.remove(id);
      setFonts((prev) => prev.filter((f) => f.id !== id));
    } catch {}
  }

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Font Library</h1>
          <p className="page-subtitle">
            {fonts.length} font{fonts.length !== 1 ? "s" : ""} in your collection
          </p>
        </div>
        <div className="page-actions">
          {/* Folder upload */}
          <div className="folder-upload-wrap">
            <select
              className="form-select-sm"
              value={uploadLicense}
              onChange={(e) => setUploadLicense(e.target.value)}
            >
              {LICENSE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <button
              className="btn btn-secondary"
              onClick={() => folderInputRef.current?.click()}
              disabled={addLoading}
            >
              Upload Folder
            </button>
            <input
              ref={folderInputRef}
              type="file"
              style={{ display: "none" }}
              // @ts-ignore - non-standard but widely supported
              webkitdirectory=""
              multiple
              accept=".ttf,.otf,.woff,.woff2,.eot,.svg"
              onChange={handleFolderUpload}
            />
          </div>
          <button className="btn btn-primary" onClick={() => { setShowAdd(true); setUploadResult(null); }}>
            Add Font
          </button>
        </div>
      </div>

      {/* Upload result toast */}
      {uploadResult && (
        <div className="upload-result">
          <strong>Upload complete:</strong> {uploadResult.added.length} font
          {uploadResult.added.length !== 1 ? "s" : ""} added
          {uploadResult.skipped.length > 0 && `, ${uploadResult.skipped.length} skipped`}.
          {uploadResult.added.length > 0 && (
            <span className="upload-added"> Added: {uploadResult.added.join(", ")}</span>
          )}
          <button className="upload-result-close" onClick={() => setUploadResult(null)}>
            ×
          </button>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      {/* Font grid */}
      {fonts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">Aa</div>
          <h3>Your font library is empty</h3>
          <p>
            Add fonts by name, pick from the catalog, or upload a folder of font
            files. We store only the font name — no font files are kept.
          </p>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            Add your first font
          </button>
        </div>
      ) : (
        <div className="font-grid">
          {fonts.map((font) => (
            <div
              key={font.id}
              className="font-card"
              onClick={() => navigate(`/library/${font.id}`)}
            >
              <div className="font-card-preview">
                <span className="font-card-preview-text">{font.font_name.slice(0, 2)}</span>
              </div>
              <div className="font-card-body">
                <h3 className="font-card-name">{font.font_name}</h3>
                {font.foundry && (
                  <p className="font-card-foundry">{font.foundry}</p>
                )}
                <div className="font-card-badges">
                  {font.category && (
                    <span
                      className="badge"
                      style={{
                        background: `${CATEGORY_COLORS[font.category] ?? "#6b6b6b"}18`,
                        color: CATEGORY_COLORS[font.category] ?? "#6b6b6b",
                        border: `1px solid ${CATEGORY_COLORS[font.category] ?? "#6b6b6b"}30`,
                      }}
                    >
                      {font.category}
                    </span>
                  )}
                  {font.license_type && (
                    <span className="badge badge-lic">{font.license_type}</span>
                  )}
                  <SourceBadge source={font.source} />
                  {!font.has_license_data && (
                    <span className="badge badge-warn">No license data</span>
                  )}
                </div>
              </div>
              <button
                className="font-card-remove"
                onClick={(e) => { e.stopPropagation(); handleRemove(font.id); }}
                title="Remove from library"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add font modal */}
      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Add Font</h2>
              <button className="modal-close" onClick={() => setShowAdd(false)}>×</button>
            </div>

            {/* Tabs */}
            <div className="modal-tabs">
              <button
                className={`modal-tab ${addTab === "manual" ? "modal-tab--active" : ""}`}
                onClick={() => setAddTab("manual")}
              >
                By Name
              </button>
              <button
                className={`modal-tab ${addTab === "catalog" ? "modal-tab--active" : ""}`}
                onClick={() => setAddTab("catalog")}
              >
                From Catalog
              </button>
            </div>

            {addError && <div className="auth-error" style={{ margin: "0 0 16px" }}>{addError}</div>}

            {addTab === "manual" ? (
              <div className="modal-body">
                <div className="form-field">
                  <label className="form-label">Font name</label>
                  <input
                    className="form-input"
                    placeholder="e.g. Helvetica, Arial, Futura"
                    value={addName}
                    onChange={(e) => setAddName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddManual()}
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">License type</label>
                  <select
                    className="form-input"
                    value={addLicense}
                    onChange={(e) => setAddLicense(e.target.value)}
                  >
                    {LICENSE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-primary btn-full"
                  onClick={handleAddManual}
                  disabled={addLoading || !addName.trim()}
                >
                  {addLoading ? "Adding…" : "Add to library"}
                </button>
              </div>
            ) : (
              <div className="modal-body">
                <div className="form-field">
                  <label className="form-label">License type</label>
                  <select
                    className="form-input"
                    value={addLicense}
                    onChange={(e) => setAddLicense(e.target.value)}
                  >
                    {LICENSE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <input
                  className="form-input"
                  placeholder="Search catalog…"
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)}
                  style={{ marginBottom: 12 }}
                />
                <ul className="catalog-list">
                  {catalogFonts.map((f) => (
                    <li key={f.id} className="catalog-item">
                      <div>
                        <span className="catalog-item-name">{f.name}</span>
                        {f.foundry && (
                          <span className="catalog-item-foundry"> — {f.foundry}</span>
                        )}
                        <div className="catalog-item-licenses">
                          {f.license_types.map((lt) => (
                            <span key={lt} className="badge badge-lic">{lt}</span>
                          ))}
                        </div>
                      </div>
                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: 13, padding: "6px 14px" }}
                        onClick={() => handleAddFromCatalog(f.id)}
                        disabled={addLoading}
                      >
                        Add
                      </button>
                    </li>
                  ))}
                  {catalogFonts.length === 0 && (
                    <li className="catalog-empty">No fonts found</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
