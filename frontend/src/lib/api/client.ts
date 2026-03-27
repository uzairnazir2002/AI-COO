"use client";

import { z } from "zod";

import { apiPaths } from "@/lib/api/endpoints";
import { emitApiClientEvent } from "@/lib/api/events";
import { meSchema, tokenSchema, type MeResponse, type TokenResponse } from "@/lib/api/schemas";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/tokens";

const baseUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const authMode = process.env.NEXT_PUBLIC_AUTH_MODE || "bearer";
const cookieMode = authMode === "cookie";
const csrfCookieName = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME || "ai_coo_csrf_token";
const csrfHeaderName = process.env.NEXT_PUBLIC_CSRF_HEADER_NAME || "X-CSRF-Token";

type ApiOptions = RequestInit & {
  skipAuth?: boolean;
  schema?: z.ZodTypeAny;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message);
  }
}

let refreshPromise: Promise<string | null> | null = null;
let lastAuthExpiredEventAt = 0;

function emitAuthExpired(path: string, message: string, status = 401) {
  const now = Date.now();
  if (now - lastAuthExpiredEventAt < 2000) return;
  lastAuthExpiredEventAt = now;
  emitApiClientEvent({
    kind: "auth_expired",
    path,
    status,
    message,
  });
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const cookie = document.cookie.split("; ").find((entry) => entry.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : null;
}

function withCsrf(headers: Headers, method: string | undefined) {
  if (!cookieMode) return;
  const normalized = (method || "GET").toUpperCase();
  if (["GET", "HEAD", "OPTIONS"].includes(normalized)) return;
  if (headers.has("Authorization")) return;
  const csrf = readCookie(csrfCookieName);
  if (csrf) headers.set(csrfHeaderName, csrf);
}

async function parseError(res: Response): Promise<ApiError> {
  const raw = await res.text();
  try {
    const parsed = JSON.parse(raw) as { detail?: string; message?: string };
    return new ApiError(parsed.message || parsed.detail || raw || res.statusText, res.status, parsed);
  } catch {
    return new ApiError(raw || res.statusText, res.status);
  }
}

async function refreshToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    if (!cookieMode && !getRefreshToken()) {
      clearTokens();
      return null;
    }

    const body = cookieMode
      ? {}
      : (() => {
          const refresh = getRefreshToken();
          return refresh ? { refresh_token: refresh } : {};
        })();

    const headers = new Headers({ "Content-Type": "application/json" });
    withCsrf(headers, "POST");

    const res = await fetch(`${baseUrl}${apiPaths.refresh}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      credentials: "include",
    });

    if (!res.ok) {
      clearTokens();
      return null;
    }

    const data = tokenSchema.parse((await res.json()) as TokenResponse);
    if (!cookieMode && data.access_token && data.refresh_token) {
      setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    }

    return "cookie-auth";
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

type ApiRawOptions = RequestInit & {
  skipAuth?: boolean;
};

export async function apiFetchRaw(path: string, options?: ApiRawOptions): Promise<Response> {
  const headers = new Headers(options?.headers ?? {});
  const method = options?.method || "GET";

  if (!options?.skipAuth && !cookieMode) {
    const access = getAccessToken();
    if (access) headers.set("Authorization", `Bearer ${access}`);
  }

  if (!(options?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  headers.set("X-Request-ID", crypto.randomUUID());
  withCsrf(headers, method);

  const run = async () => {
    try {
      return await fetch(`${baseUrl}${path}`, {
        ...options,
        method,
        headers,
        credentials: "include",
        cache: "no-store",
      });
    } catch (err) {
      emitApiClientEvent({
        kind: "network_error",
        path,
        status: 0,
        message: "Network request failed. Check API availability or CORS configuration.",
      });
      throw new ApiError(err instanceof Error ? err.message : "Network request failed", 0);
    }
  };

  let res = await run();
  if (res.status === 401 && !options?.skipAuth) {
    const refreshed = await refreshToken();
    if (!refreshed) {
      emitAuthExpired(path, "Session expired. Please sign in again.");
      throw await parseError(res);
    }
    if (!cookieMode && refreshed !== "cookie-auth") {
      headers.set("Authorization", `Bearer ${refreshed}`);
    }
    withCsrf(headers, method);
    res = await run();
  }

  if (!res.ok) {
    if (res.status === 401 && !options?.skipAuth) {
      emitAuthExpired(path, "Session expired. Please sign in again.");
    }
    throw await parseError(res);
  }

  return res;
}

export async function api<T>(path: string, options?: ApiOptions): Promise<T> {
  const res = await apiFetchRaw(path, options);

  if (res.status === 204) {
    return undefined as T;
  }

  const json = await res.json();
  if (options?.schema) {
    return options.schema.parse(json) as T;
  }
  return json as T;
}

export async function bootstrapSession(): Promise<MeResponse> {
  return api<MeResponse>(apiPaths.me, { schema: meSchema });
}

export async function logout(refreshTokenValue?: string) {
  const body = cookieMode ? {} : { refresh_token: refreshTokenValue ?? getRefreshToken() };
  try {
    await api<{ ok: boolean }>(apiPaths.logout, {
      method: "POST",
      body: JSON.stringify(body),
    });
  } finally {
    clearTokens();
  }
}
