"use client";

import { Button } from "@/components/ui/button";

export function PromptSuggestions({
  prompts,
  onSelect,
}: {
  prompts: string[];
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/70 p-3" data-testid="ai-chat-suggested-prompts">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Suggested prompts</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {prompts.map((prompt) => (
          <Button key={prompt} size="sm" variant="outline" onClick={() => onSelect(prompt)}>
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  );
}

