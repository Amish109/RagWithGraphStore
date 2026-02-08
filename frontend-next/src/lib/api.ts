const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }
  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", { method: "POST" });
      return res.ok;
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (res.status === 401) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return fetch(url, {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });
    }
    window.location.href = "/login";
  }

  return res;
}

export async function apiUpload(
  path: string,
  formData: FormData
): Promise<Response> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (res.status === 401) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return fetch(url, {
        method: "POST",
        body: formData,
        credentials: "include",
      });
    }
    window.location.href = "/login";
  }

  return res;
}

export { API_URL };
