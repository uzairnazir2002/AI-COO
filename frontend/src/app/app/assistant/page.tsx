"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { StatusStrip } from "@/components/layout/status-strip";
import { Button } from "@/components/ui/button";
import { AssistantWorkspaceContainer } from "@/features/ai-chat/containers/assistant-workspace-container";
import { useAiChatSession, useAiChatSessions, useCreateAiChatSession, useSendAiChatMessage } from "@/features/ai-chat/hooks";
import { buildSuggestedPrompts } from "@/features/ai-chat/services/suggested-prompts";
import { useAppStore } from "@/store/appStore";

export default function AssistantPage() {
  const selectedOrgId = useAppStore((s) => s.selectedOrgId);
  const selectedOrg = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId));
  const range = useAppStore((s) => s.globalDateRange);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const toast = useToast();

  const sessions = useAiChatSessions({ mineOnly: false, limit: 40 });
  const createSession = useCreateAiChatSession();
  const sendMessage = useSendAiChatMessage();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("chat");
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
  const sessionsError = sessions.error instanceof Error ? sessions.error.message : null;
  const detailError = detail.error instanceof Error ? detail.error.message : null;
  const suggestedPrompts = useMemo(
    () =>
      buildSuggestedPrompts({
        from: range.from,
        to: range.to,
        locationId: selectedLocationId,
        hasMessages: messages.length > 0,
      }),
    [range.from, range.to, selectedLocationId, messages.length],
  );
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

      <StatusStrip
        items={[
          { label: "Sessions", value: String(sessions.data?.length ?? 0), tone: "neutral" },
          { label: "Scope", value: `${range.from} to ${range.to}`, tone: "neutral" },
          { label: "Location", value: selectedLocationId || "All", tone: "neutral" },
        ]}
      />

      {sessions.isLoading && !sessions.data ? <SkeletonPanel rows={5} /> : null}

      {sessionsError ? (
        <div className="space-y-3">
          <InlineErrorBanner message={sessionsError} />
          <RetryCard message="Unable to load AI chat sessions." onRetry={() => void sessions.refetch()} />
        </div>
      ) : null}

      {detailError ? (
        <div className="space-y-3">
          <InlineErrorBanner message={detailError} />
          <RetryCard message="Unable to load selected conversation." onRetry={() => void detail.refetch()} />
        </div>
      ) : null}

      <AssistantWorkspaceContainer
        activeTab={activeTab}
        onTabChange={setActiveTab}
        sessionsLoading={sessions.isLoading}
        sessionsData={sessions.data || []}
        activeSessionId={activeSessionId}
        onSessionSelect={setActiveSessionId}
        sessionTitle={sessionTitle}
        detailLoading={detail.isLoading}
        detailError={detail.error}
        messages={messages}
        messageInput={messageInput}
        onMessageInputChange={setMessageInput}
        onSend={onSend}
        sendPending={sendMessage.isPending}
        createSessionPending={createSession.isPending}
        rangeFrom={range.from}
        rangeTo={range.to}
        selectedOrgName={selectedOrg?.name || "Unknown org"}
        selectedLocationId={selectedLocationId}
        suggestedPrompts={suggestedPrompts}
        onUsePrompt={(prompt) => setMessageInput(prompt)}
      />
    </div>
  );
}

