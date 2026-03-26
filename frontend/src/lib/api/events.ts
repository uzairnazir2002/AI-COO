"use client";

export type ApiClientEventDetail =
  | {
      kind: "auth_expired";
      path: string;
      status: number;
      message: string;
    }
  | {
      kind: "network_error";
      path: string;
      status: 0;
      message: string;
    };

export const API_CLIENT_EVENT_NAME = "ai-coo:api-client-event";

export function emitApiClientEvent(detail: ApiClientEventDetail) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<ApiClientEventDetail>(API_CLIENT_EVENT_NAME, { detail }));
}

