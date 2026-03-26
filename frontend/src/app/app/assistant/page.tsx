"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAiChatSession, useAiChatSessions, useCreateAiChatSession, useSendAiChatMessage } from "@/features/ai-chat/hooks";
import { cn } from "@/lib/utils/cn";
import { useAppStore } from "@/store/appStore";

export default function AssistantPage() {
  const selectedOrgId = useAppStore((s) => s.selectedOrgId);
  const selectedOrg = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId));
  const range = useAppStore((s) => s.globalDateRange);
  const toast = useToast();

  const sessions = useAiChatSessions({ mineOnly: false, limit: 40 });
  const createSession = useCreateAiChatSession();
  const sendMessage = useSendAiChatMessage();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messageInput, setMessageInput] = useState("");
  const detail = useAiChatSession(activeSessionId);

  useEffect(() => {
    if (activeSessionId) return;
    const first = sessions.data?.[0];
    if (first) {
      setActiveSessionId(first.id);
    }
  }, [activeSessionId, sessions.data]);

  const messages = detail.data?.messages ?? [];
  const hasMessages = messages.length > 0;
  const sessionTitle = useMemo(() => {
    if (!activeSessionId) return "No active chat";
    const match = sessions.data?.find((session) => session.id === activeSessionId);
    return match?.title || "AI chat session";
  }, [activeSessionId, sessions.data]);

  if (!selectedOrgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Select an organization to open AI Chat."
        description="AI chat is organization-scoped and grounded on org analytics and alerts."
      />
    );
  }

  if (sessions.error) {
    return <ErrorState description={String((sessions.error as Error).message || sessions.error)} />;
  }

  async function onNewChat() {
    try {
      const created = await createSession.mutateAsync({ title: "New AI chat" });
      setActiveSessionId(created.id);
      setMessageInput("");
      toast.toast({ title: "New chat started", variant: "success" });
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Failed to create chat session", variant: "danger" });
    }
  }

  async function onSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = messageInput.trim();
    if (!message) return;
    let sessionId = activeSessionId;
    try {
      if (!sessionId) {
        const created = await createSession.mutateAsync({ title: "New AI chat" });
        sessionId = created.id;
        setActiveSessionId(created.id);
      }
      await sendMessage.mutateAsync({
        sessionId,
        message,
        from: range.from,
        to: range.to,
      });
      setMessageInput("");
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Failed to send message", variant: "danger" });
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="AI Chat"
        description={`Grounded assistant scoped to ${selectedOrg?.name || "selected org"} metrics from ${range.from} to ${range.to}.`}
        actions={
          <Button onClick={onNewChat} disabled={createSession.isPending} data-testid="ai-chat-new-session">
            New chat
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Sessions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sessions.isLoading ? <p className="text-sm text-muted-foreground">Loading sessions...</p> : null}
            {!sessions.isLoading && (sessions.data?.length || 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No sessions yet. Start a new chat.</p>
            ) : null}
            {(sessions.data || []).map((session) => (
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
                onClick={() => setActiveSessionId(session.id)}
              >
                <p className="line-clamp-1 text-sm font-medium">{session.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{new Date(session.last_activity_at).toLocaleString()}</p>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{sessionTitle}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {detail.error ? <ErrorState description={String((detail.error as Error).message || detail.error)} /> : null}
            {detail.isLoading ? <p className="text-sm text-muted-foreground">Loading conversation...</p> : null}
            {!detail.isLoading && !detail.error && !hasMessages ? (
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

            <form className="space-y-2" onSubmit={onSend}>
              <textarea
                value={messageInput}
                onChange={(event) => setMessageInput(event.target.value)}
                placeholder="Ask a business question..."
                rows={4}
                className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm outline-none ring-offset-background transition focus-visible:ring-2 focus-visible:ring-ring"
                data-testid="ai-chat-composer"
              />
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  Time scope: {range.from} to {range.to}
                </p>
                <Button type="submit" disabled={sendMessage.isPending || createSession.isPending || !messageInput.trim()} data-testid="ai-chat-send">
                  {sendMessage.isPending ? "Sending..." : "Send"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
