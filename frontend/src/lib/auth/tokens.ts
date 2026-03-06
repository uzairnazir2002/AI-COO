"use client";

const ACCESS = "ai_coo_access_token";
const REFRESH = "ai_coo_refresh_token";

function readStorage(key: string) {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures and let the app rely on server state.
  }
}

function removeStorage(key: string) {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(key);
  } catch {
    // Ignore storage failures during cleanup.
  }
}

export function getAccessToken() {
  return readStorage(ACCESS);
}

export function getRefreshToken() {
  return readStorage(REFRESH);
}

export function setTokens(access: string, refresh: string) {
  writeStorage(ACCESS, access);
  writeStorage(REFRESH, refresh);
}

export function clearTokens() {
  removeStorage(ACCESS);
  removeStorage(REFRESH);
}
