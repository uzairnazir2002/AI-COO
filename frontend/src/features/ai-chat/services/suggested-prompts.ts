type PromptContext = {
  from: string;
  to: string;
  locationId: string | null;
  hasMessages: boolean;
};

export function buildSuggestedPrompts(context: PromptContext): string[] {
  const locationLabel = context.locationId ? `for location ${context.locationId}` : "across all locations";
  const prompts = [
    `What changed in cashflow between ${context.from} and ${context.to} ${locationLabel}?`,
    `Which expense categories are driving runway pressure ${locationLabel}?`,
    `Who was absent most between ${context.from} and ${context.to} ${locationLabel}?`,
    `Which department has the highest overtime risk ${locationLabel}?`,
    `Summarize workforce risk this week ${locationLabel}.`,
    `What is the labor cost trend from ${context.from} to ${context.to} ${locationLabel}?`,
    `Which employees are repeatedly late in this period ${locationLabel}?`,
    `Summarize top anomalies and likely root causes in this period.`,
    `What are the highest-confidence actions to improve net margin next month?`,
  ];
  if (!context.hasMessages) {
    return prompts.slice(0, 3);
  }
  return prompts;
}
