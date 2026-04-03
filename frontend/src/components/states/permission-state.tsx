"use client";

export function PermissionState({
  message,
}: {
  message: string;
}) {
  return <p className="text-sm text-muted-foreground">{message}</p>;
}

