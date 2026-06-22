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

// ── Scan ──────────────────────────────────────────────────────────────────────

export const scanApi = {
  analyze: (url: string) =>
    request<import("./types").AnalysisResult>("POST", "/analyze", { url }),
};

// ── History ───────────────────────────────────────────────────────────────────

export const historyApi = {
  list: ({
    limit = 20,
    offset = 0,
    url,
    min_score,
    max_score,
  }: import("./types").HistoryListParams = {}) => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (url?.trim()) params.set("url", url.trim());
    if (min_score != null && !Number.isNaN(min_score)) {
      params.set("min_score", String(min_score));
    }
    if (max_score != null && !Number.isNaN(max_score)) {
      params.set("max_score", String(max_score));
    }
    return request<import("./types").PaginatedScans>("GET", `/history?${params}`);
  },
  get: (id: number) => request<import("./types").ScanDetail>("GET", `/history/${id}`),
};
