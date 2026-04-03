"use client";

import type { FormEvent } from "react";
import Link from "next/link";

import { PromptSuggestions } from "@/components/ai/prompt-suggestions";
import { ErrorState } from "@/components/common/error-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { TabNav } from "@/components/layout/tab-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";
import type { AiChatMessage, AiChatSession } from "@/types/domain";

export function AssistantWorkspaceContainer({
  activeTab,
  onTabChange,
  sessionsLoading,
  sessionsData,
  activeSessionId,
  onSessionSelect,
  sessionTitle,
  detailLoading,
  detailError,
  messages,
  messageInput,
  onMessageInputChange,
  onSend,
  sendPending,
  createSessionPending,
  rangeFrom,
  rangeTo,
  selectedOrgName,
  selectedLocationId,
  suggestedPrompts,
  onUsePrompt,
}: {
  activeTab: string;
  onTabChange: (tab: string) => void;
  sessionsLoading: boolean;
  sessionsData: AiChatSession[];
  activeSessionId: string | null;
  onSessionSelect: (id: string) => void;
  sessionTitle: string;
  detailLoading: boolean;
  detailError: unknown;
  messages: AiChatMessage[];
  messageInput: string;
  onMessageInputChange: (value: string) => void;
  onSend: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  sendPending: boolean;
  createSessionPending: boolean;
  rangeFrom: string;
  rangeTo: string;
  selectedOrgName: string;
  selectedLocationId: string | null;
  suggestedPrompts: string[];
  onUsePrompt: (prompt: string) => void;
}) {
  const hasMessages = messages.length > 0;

  return (
    <>
      <TabNav
        active={activeTab}
        onChange={onTabChange}
        items={[
          { id: "chat", label: "Chat Workspace" },
          { id: "context", label: "Context" },
        ]}
      />

      {activeTab === "chat" ? (
        <section className="grid gap-4 xl:grid-cols-[320px_1fr]">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Sessions</h2>
            </PanelHeader>
            <PanelBody className="space-y-2">
              {sessionsLoading ? <p className="text-sm text-muted-foreground">Loading sessions...</p> : null}
              {!sessionsLoading && sessionsData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No sessions yet. Start a new chat.</p>
              ) : null}
              {sessionsData.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  data-testid="ai-chat-session-item"
                  className={cn(
                    "w-full rounded-2xl border px-3 py-2 text-left",
                    activeSessionId === session.id
                      ? "border-primary/60 bg-primary/10"
                      : "border-border/70 hover:bg-muted",
                  )}
                  onClick={() => onSessionSelect(session.id)}
                >
                  <p className="line-clamp-1 text-sm font-medium">{session.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{new Date(session.last_activity_at).toLocaleString()}</p>
                </button>
              ))}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">{sessionTitle}</h2>
            </PanelHeader>
            <PanelBody className="space-y-4">
              {detailError ? <ErrorState description={String((detailError as Error).message || detailError)} /> : null}
              {detailLoading ? <p className="text-sm text-muted-foreground">Loading conversation...</p> : null}
              {!detailLoading && !detailError && !hasMessages ? (
                <p className="text-sm text-muted-foreground">
                  Ask a question about cashflow, runway, budget variance, forecasts, or active alerts.
                </p>
              ) : null}

              <div className="max-h-[460px] space-y-3 overflow-y-auto rounded-2xl border border-border/70 bg-card/45 p-3" data-testid="ai-chat-messages">
                {messages.map((message) => {
                  const isUser = message.role.toUpperCase() === "USER";
                  const isAssistant = message.role.toUpperCase() === "ASSISTANT";
                  return (
                    <div key={message.id} className={cn("flex", isUser ? "justify-end" : "justify-start")} data-testid={isAssistant ? "ai-chat-assistant-message" : "ai-chat-user-message"}>
                      <div
                        className={cn(
                          "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
                          isUser ? "bg-primary text-primary-foreground" : "border border-border/70 bg-background",
                        )}
                      >
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-[11px] font-semibold uppercase tracking-[0.2em] opacity-80">
                            {isUser ? "You" : message.role}
                          </span>
                          {isAssistant ? (
                            message.fallback_used ? (
                              <Badge variant="warning">Fallback</Badge>
                            ) : (
                              <Badge variant="secondary">Grounded</Badge>
                            )
                          ) : null}
                        </div>
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                        {isAssistant && message.grounding_violations.length > 0 ? (
                          <p className="mt-2 text-xs text-warning">
                            Grounding validator fallback: {message.grounding_violations.join("; ")}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>

              <form className="space-y-2" onSubmit={(event) => void onSend(event)}>
                <textarea
                  value={messageInput}
                  onChange={(event) => onMessageInputChange(event.target.value)}
                  placeholder="Ask a business question..."
                  rows={4}
                  className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm outline-none ring-offset-background transition focus-visible:ring-2 focus-visible:ring-ring"
                  data-testid="ai-chat-composer"
                />
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    Time scope: {rangeFrom} to {rangeTo}
                  </p>
                  <Button type="submit" disabled={sendPending || createSessionPending || !messageInput.trim()} data-testid="ai-chat-send">
                    {sendPending ? "Sending..." : "Send"}
                  </Button>
                </div>
              </form>

              <PromptSuggestions prompts={suggestedPrompts} onSelect={onUsePrompt} />
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      {activeTab === "context" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Grounding context</h2>
            </PanelHeader>
            <PanelBody className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
                <p className="text-xs uppercase text-muted-foreground">Organization</p>
                <p className="mt-2 text-sm font-semibold">{selectedOrgName}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
                <p className="text-xs uppercase text-muted-foreground">Date scope</p>
                <p className="mt-2 text-sm font-semibold">{rangeFrom} to {rangeTo}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
                <p className="text-xs uppercase text-muted-foreground">Location scope</p>
                <p className="mt-2 text-sm font-semibold">{selectedLocationId || "All locations"}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/70 p-4 md:col-span-3">
                <p className="text-xs uppercase text-muted-foreground">Cited surfaces</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  <Link className="rounded border border-border/70 px-2 py-1 hover:bg-muted" href="/app/dashboard">Dashboard metrics</Link>
                  <Link className="rounded border border-border/70 px-2 py-1 hover:bg-muted" href="/app/transactions">Transactions</Link>
                  <Link className="rounded border border-border/70 px-2 py-1 hover:bg-muted" href="/app/forecast">Forecast</Link>
                  <Link className="rounded border border-border/70 px-2 py-1 hover:bg-muted" href="/app/alerts">Alerts</Link>
                </div>
              </div>
            </PanelBody>
          </Panel>
        </section>
      ) : null}
    </>
  );
}
