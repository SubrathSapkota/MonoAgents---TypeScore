const BASE = "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("ts_token");
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isFormData = false
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isFormData && body) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isFormData
      ? (body as FormData)
      : body
      ? JSON.stringify(body)
      : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, name: string, password: string) =>
    request<import("./types").AuthResponse>("POST", "/auth/register", { email, name, password }),
  login: (email: string, password: string) =>
    request<import("./types").AuthResponse>("POST", "/auth/login", { email, password }),
};

// ── Font catalog ──────────────────────────────────────────────────────────────

export const fontsApi = {
  list: (q?: string, category?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    const qs = params.toString();
    return request<import("./types").FontSummary[]>("GET", `/fonts${qs ? `?${qs}` : ""}`);
  },
  get: (id: number) => request<import("./types").FontDetail>("GET", `/fonts/${id}`),
};

// ── User font library ─────────────────────────────────────────────────────────

export const userFontsApi = {
  list: () => request<import("./types").UserFont[]>("GET", "/user/fonts"),
  get: (id: number) => request<import("./types").UserFontDetail>("GET", `/user/fonts/${id}`),
  add: (payload: { font_name?: string; font_id?: number; license_type?: string }) =>
    request<import("./types").UserFont>("POST", "/user/fonts", payload),
  uploadFolder: (files: FileList, licenseType?: string) => {
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    if (licenseType) form.append("license_type", licenseType);
    return request<{ added: string[]; skipped: string[]; count: number }>(
      "POST",
      "/user/fonts/upload-folder",
      form,
      true
    );
  },
  remove: (id: number) => request<void>("DELETE", `/user/fonts/${id}`),
};

// ── Scan ──────────────────────────────────────────────────────────────────────

export const scanApi = {
  analyze: (url: string) =>
    request<import("./types").AnalysisResult>("POST", "/analyze", { url }),
};

// ── History ───────────────────────────────────────────────────────────────────

export const historyApi = {
  list: (limit = 20, offset = 0) =>
    request<import("./types").ScanSummary[]>("GET", `/history?limit=${limit}&offset=${offset}`),
  get: (id: number) => request<import("./types").ScanDetail>("GET", `/history/${id}`),
};
