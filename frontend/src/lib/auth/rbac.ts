import type { Role } from "@/types/domain";

export function canEdit(role: Role | undefined) {
  return role === "OWNER" || role === "EDITOR";
}

export function isOwner(role: Role | undefined) {
  return role === "OWNER";
}
