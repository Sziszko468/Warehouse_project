const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

let authToken: string | null = null;
export function setAuthToken(token: string | null) {
  authToken = token;
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** form-urlencoded body, used only for the OAuth2 password login endpoint */
  form?: Record<string, string>;
}

function buildQuery(query?: RequestOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function extractDetail(payload: unknown): string | null {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => (entry && typeof entry === "object" && "msg" in entry ? String((entry as { msg: unknown }).msg) : String(entry)))
        .join("; ");
    }
  }
  return null;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, form } = options;
  const headers: Record<string, string> = {};
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  let requestBody: BodyInit | undefined;
  if (form) {
    requestBody = new URLSearchParams(form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    requestBody = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_URL}${path}${buildQuery(query)}`, {
    method,
    headers,
    body: requestBody,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    if (response.status === 401) onUnauthorized?.();
    throw new ApiError(response.status, extractDetail(payload) ?? `Hiba történt (${response.status}).`);
  }

  return payload as T;
}

/**
 * Downloads a file (e.g. a CSV export) and saves it via the browser - a plain `<a href>` can't
 * attach the bearer token, so this fetches with the same auth header apiRequest uses, then
 * triggers the save through a temporary object URL.
 */
export async function downloadFile(path: string, query?: RequestOptions["query"]): Promise<void> {
  const headers: Record<string, string> = {};
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const response = await fetch(`${API_URL}${path}${buildQuery(query)}`, { headers });
  if (!response.ok) {
    if (response.status === 401) onUnauthorized?.();
    const text = await response.text();
    let payload: unknown = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = text;
    }
    throw new ApiError(response.status, extractDetail(payload) ?? `Hiba történt (${response.status}).`);
  }

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filenameMatch = /filename="?([^"]+)"?/.exec(disposition);
  const filename = filenameMatch?.[1] ?? "export.csv";

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
