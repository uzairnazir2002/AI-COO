import type { Alert } from "@/types/domain";

export type AlertRecommendationAction = "assign_to_me" | "acknowledge" | "dismiss";

export type AlertRecommendation = {
  id: string;
  label: string;
  description: string;
  action: AlertRecommendationAction;
};

export function getAlertRecommendations(alert: Alert, isAssignedToMe: boolean): AlertRecommendation[] {
  const items: AlertRecommendation[] = [];

  if (!isAssignedToMe) {
    items.push({
      id: "assign-to-me",
      label: "Assign to me",
      description: "Take direct ownership before triage to avoid response drift.",
      action: "assign_to_me",
    });
  }

  if (!alert.acknowledged_at) {
    items.push({
      id: "acknowledge",
      label: "Acknowledge signal",
      description: "Mark this alert as reviewed while you investigate root cause.",
      action: "acknowledge",
    });
  }

  if (alert.status === "OPEN" && alert.severity !== "HIGH") {
    items.push({
      id: "dismiss-low-confidence",
      label: "Dismiss if resolved",
      description: "Dismiss low/medium severity alerts when mitigation is complete.",
      action: "dismiss",
    });
  }

  if (items.length === 0) {
    items.push({
      id: "acknowledge-default",
      label: "Acknowledge update",
      description: "Keep the trail current while work is in progress.",
      action: "acknowledge",
    });
  }

  return items.slice(0, 3);
}
