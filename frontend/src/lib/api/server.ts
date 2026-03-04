import { cookies } from "next/headers";

const baseUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const selectedOrgCookie = "ai_coo_selected_org";

export async function getServerSelectedOrgId() {
  const store = await cookies();
  return store.get(selectedOrgCookie)?.value || null;
}

async function serverFetch(path: string, init?: RequestInit) {
  const store = await cookies();
  const cookieHeader = store.toString();
  const res = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      cookie: cookieHeader,
    },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function serverApiGet<T>(path: string): Promise<T | null> {
  return (await serverFetch(path, { method: "GET" })) as T | null;
}

export async function serverApiPost<T>(path: string, body: unknown): Promise<T | null> {
  return (await serverFetch(path, { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } })) as T | null;
}

export async function resolveServerOrgId(): Promise<string | null> {
  const selected = await getServerSelectedOrgId();
  if (selected) return selected;
  const me = await serverApiGet<{ orgs: Array<{ org_id: string }> }>("/api/v1/auth/me");
  return me?.orgs?.[0]?.org_id ?? null;
}
