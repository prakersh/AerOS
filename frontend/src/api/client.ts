/** AEROS API client — thin fetch wrapper with credential forwarding. */

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl;
  }

  private getCsrfToken(): string {
    const match = document.cookie.match(/(?:^|;\s*)aeros_csrf=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (method !== "GET" && method !== "HEAD") {
      const csrf = this.getCsrfToken();
      if (csrf) headers["x-csrf-token"] = csrf;
    }

    const res = await fetch(url, {
      method,
      headers,
      credentials: "include",
      body: body != null ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const error: ApiError = {
        status: res.status,
        message: errorBody.detail ?? errorBody.message ?? res.statusText,
        detail: errorBody,
      };
      throw error;
    }

    // 204 No Content
    if (res.status === 204) {
      return undefined as T;
    }

    return res.json() as Promise<T>;
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PUT", path, body);
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PATCH", path, body);
  }

  async del<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }

  async upload<T>(path: string, file: File): Promise<T> {
    const formData = new FormData();
    formData.append("file", file);
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {};
    const csrf = this.getCsrfToken();
    if (csrf) headers["x-csrf-token"] = csrf;
    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const error: ApiError = {
        status: res.status,
        message: errorBody.detail ?? errorBody.message ?? res.statusText,
        detail: errorBody,
      };
      throw error;
    }
    return res.json() as Promise<T>;
  }
}

export const api = new ApiClient();
