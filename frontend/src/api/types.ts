// ── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: number;
  email: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

// ── Font catalog ──────────────────────────────────────────────────────────────

export type LicenseType = "desktop" | "webfont" | "app" | "edoc" | "digital_ad";

export const LICENSE_LABELS: Record<LicenseType, string> = {
  desktop: "Desktop",
  webfont: "Webfont",
  app: "App",
  edoc: "Electronic Doc",
  digital_ad: "Digital Ad",
};

export interface LicenseItem {
  name: string;
  description: string;
  link?: string;
}

export interface FontLicense {
  id: number;
  license_type: LicenseType;
  can_use: LicenseItem[];
  cannot_use: LicenseItem[];
  description?: string;
  eula_url?: string;
}

export interface FontSummary {
  id: number;
  name: string;
  foundry?: string;
  category?: string;
  description?: string;
  license_types: LicenseType[];
}

export interface FontDetail extends FontSummary {
  licenses: FontLicense[];
}

// ── User font library ─────────────────────────────────────────────────────────

export interface UserFont {
  id: number;
  font_name: string;
  foundry?: string;
  category?: string;
  license_type?: LicenseType;
  source: "catalog" | "upload" | "manual";
  catalog_id?: number;
  has_license_data: boolean;
  added_at: string;
}

export interface UserFontDetail extends UserFont {
  description?: string;
  licenses: FontLicense[];
}

// ── Scan / Analysis ───────────────────────────────────────────────────────────

export interface PageResult {
  url: string;
  path: string;
  fonts: string[];
  css_files: string[];
  inline_styles: string[];
  error?: string;
}

export interface MetricBreakdown {
  score: number;
  weight: number;
  violations: string[];
}

export interface Violation {
  id: string;
  impact: string;
  count: number;
  description: string;
}

export interface AnalysisResult {
  base_url: string;
  pages: PageResult[];
  lighthouse: {
    performance: number;
    lcp_ms: number;
    cls: number;
    font_warnings: string[];
  } | null;
  accessibility: {
    total_violations: number;
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
    violations: Violation[];
  } | null;
  scores: {
    overall_score: number;
    breakdown: Record<string, MetricBreakdown>;
  };
  scan_id?: number;
}

// ── Scan history ──────────────────────────────────────────────────────────────

export interface ScanScores {
  brand_consistency?: number;
  license_compliance?: number;
  performance?: number;
  accessibility?: number;
  developer_experience?: number;
}

export interface ScanSummary {
  id: number;
  url: string;
  overall_score?: number;
  scores: ScanScores;
  issues_count: number;
  created_at: string;
}

export interface ScanDetail extends ScanSummary {
  issues: { metric: string; message: string }[];
  raw_data: Record<string, unknown>;
}

export interface PaginatedScans {
  items: ScanSummary[];
  total: number;
  limit: number;
  offset: number;
}
