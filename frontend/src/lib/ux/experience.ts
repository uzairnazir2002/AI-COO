import type { ExperienceTier, OrgRole } from "@/store/appStore";

const tierWeight: Record<ExperienceTier, number> = {
  simple: 0,
  standard: 1,
  advanced: 2,
};

export function isTierAtLeast(current: ExperienceTier, target: ExperienceTier) {
  return tierWeight[current] >= tierWeight[target];
}

export function canAccessAdvancedNav(role: OrgRole | undefined, tier: ExperienceTier) {
  return tier === "advanced" || role === "OWNER" || role === "EDITOR";
}

export function defaultTierForRole(role: OrgRole | undefined): ExperienceTier {
  if (role === "OWNER") return "standard";
  return "simple";
}

export function isSimpleTier(tier: ExperienceTier) {
  return tier === "simple";
}

