import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { userFontsApi } from "../api/client";
import type { UserFontDetail, FontLicense, LicenseItem } from "../api/types";
import { LICENSE_LABELS } from "../api/types";

function LicenseItemRow({
  item,
  type,
}: {
  item: LicenseItem;
  type: "allow" | "deny";
}) {
  return (
    <div className={`license-item license-item--${type}`}>
      <span className={`license-item-dot license-item-dot--${type}`} />
      <div className="license-item-content">
        <span className="license-item-name">{item.name}</span>
        <span className="license-item-desc">{item.description}</span>
        {item.link && <a className="license-item-link" href="#">{item.link}</a>}
      </div>
    </div>
  );
}

function LicensePanel({ license }: { license: FontLicense }) {
  return (
    <div className="license-panel">
      {license.description && (
        <p className="license-panel-desc">{license.description}</p>
      )}
      <div className="license-panel-grid">
        <div>
          <h3 className="license-section-heading license-section-heading--can">
            ✓ Can use
          </h3>
          <div className="license-items">
            {license.can_use.map((item, i) => (
              <LicenseItemRow key={i} item={item} type="allow" />
            ))}
          </div>
        </div>
        <div>
          <h3 className="license-section-heading license-section-heading--cannot">
            ✕ Cannot use
          </h3>
          <div className="license-items">
            {license.cannot_use.map((item, i) => (
              <LicenseItemRow key={i} item={item} type="deny" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FontDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [font, setFont] = useState<UserFontDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("");

  useEffect(() => {
    if (!id) return;
    userFontsApi
      .get(Number(id))
      .then((f) => {
        setFont(f);
        if (f.licenses.length > 0) {
          setActiveTab(f.license_type ?? f.licenses[0].license_type);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !font) {
    return (
      <div className="page">
        <div className="error-banner">{error ?? "Font not found"}</div>
        <Link to="/library" className="btn btn-secondary" style={{ marginTop: 16 }}>
          Back to library
        </Link>
      </div>
    );
  }

  const activeLicense = font.licenses.find((l) => l.license_type === activeTab);

  return (
    <div className="page">
      {/* ── Breadcrumb ─────────────────────────────────────── */}
      <div className="breadcrumb">
        <Link to="/library" className="breadcrumb-link">
          Font Library
        </Link>
        <span className="breadcrumb-sep">›</span>
        <span>{font.font_name}</span>
      </div>

      {/* ── Font header ─────────────────────────────────────── */}
      <div className="font-detail-header">
        <div className="font-detail-preview">
          <span className="font-detail-preview-text">{font.font_name.slice(0, 2)}</span>
        </div>
        <div>
          <h1 className="font-detail-name">{font.font_name}</h1>
          <div className="font-detail-meta">
            {font.foundry && (
              <span className="font-detail-foundry">{font.foundry}</span>
            )}
            {font.category && (
              <span className="badge">{font.category}</span>
            )}
            {font.license_type && (
              <span className="badge badge-lic">
                {LICENSE_LABELS[font.license_type] ?? font.license_type}
              </span>
            )}
            <span className={`badge badge-source badge-source--${font.source}`}>
              {font.source === "catalog" ? "In catalog" : font.source === "upload" ? "Uploaded" : "Manually added"}
            </span>
          </div>
          {font.description && (
            <p className="font-detail-desc">{font.description}</p>
          )}
        </div>
      </div>

      {/* ── License section ──────────────────────────────────── */}
      {font.licenses.length > 0 ? (
        <div className="license-block">
          <h2 className="section-title" style={{ marginBottom: 16 }}>
            License Information
          </h2>

          {/* License type tabs */}
          <div className="license-tabs">
            {font.licenses.map((lic) => (
              <button
                key={lic.license_type}
                className={`license-tab ${activeTab === lic.license_type ? "license-tab--active" : ""}`}
                onClick={() => setActiveTab(lic.license_type)}
              >
                {LICENSE_LABELS[lic.license_type as keyof typeof LICENSE_LABELS] ?? lic.license_type}
              </button>
            ))}
          </div>

          {activeLicense && <LicensePanel license={activeLicense} />}
        </div>
      ) : (
        <div className="no-license-block">
          <div className="empty-state">
            <div className="empty-icon">?</div>
            <h3>No license data available</h3>
            <p>
              This font was added manually or uploaded and doesn't match any font
              in our catalog. License information cannot be displayed.
            </p>
            <p style={{ marginTop: 8 }}>
              Check the font foundry's website for license terms.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
