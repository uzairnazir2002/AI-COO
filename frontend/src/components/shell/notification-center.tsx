"use client";

import { useMemo, useState } from "react";
import { Bell, CheckCheck, Trash2 } from "lucide-react";
import Link from "next/link";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/common/use-toast";
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications } from "@/features/notifications/inbox-hooks";

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function NotificationCenter({ streamStatus = "idle" }: { streamStatus?: "idle" | "connecting" | "live" | "error" | "fallback_polling" }) {
  const [open, setOpen] = useState(false);
  const history = useToastStore((s) => s.history);
  const active = useToastStore((s) => s.toasts);
  const markAllRead = useToastStore((s) => s.markAllRead);
  const clearHistory = useToastStore((s) => s.clearHistory);
  const inbox = useNotifications(false);
  const markReadMutation = useMarkNotificationRead();
  const markAllNotificationsRead = useMarkAllNotificationsRead();

  const unreadCount = active.length + (inbox.data?.unread_count ?? 0);
  const items = useMemo(() => history.slice(0, 30), [history]);
  const streamLabel = streamStatus === "fallback_polling" ? "fallback polling" : streamStatus;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="relative rounded-2xl" aria-label="Open notifications">
          <Bell className="mr-2 h-4 w-4" />
          Notifications
          {unreadCount > 0 ? (
            <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[11px] font-semibold text-primary-foreground">
              {unreadCount}
            </span>
          ) : null}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Notification Center</DialogTitle>
          <DialogDescription>Durable org notifications plus session toasts. Stream status: {streamLabel}.</DialogDescription>
        </DialogHeader>
        <div className="flex items-center justify-end gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={async () => {
              markAllRead();
              await markAllNotificationsRead.mutateAsync();
            }}
          >
            <CheckCheck className="mr-2 h-4 w-4" /> Mark all read
          </Button>
          <Button size="sm" variant="ghost" onClick={clearHistory}>
            <Trash2 className="mr-2 h-4 w-4" /> Clear
          </Button>
        </div>
        <div className="max-h-[420px] space-y-4 overflow-auto pr-1">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Inbox</p>
            {(inbox.data?.items.length ?? 0) === 0 ? (
              <p className="rounded-xl border border-border/60 p-4 text-sm text-muted-foreground">No saved notifications yet.</p>
            ) : (
              inbox.data?.items.map((item) => (
                <div key={item.id} className="rounded-xl border border-border/70 bg-card/70 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">{item.title}</p>
                      {item.message ? <p className="mt-1 text-xs text-muted-foreground">{item.message}</p> : null}
                    </div>
                    <span className="text-xs text-muted-foreground">{formatTime(new Date(item.created_at).getTime())}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{item.category}</p>
                    <div className="flex items-center gap-2">
                      {item.link ? (
                        <Button asChild size="sm" variant="ghost">
                          <Link href={item.link}>Open</Link>
                        </Button>
                      ) : null}
                      {!item.is_read ? (
                        <Button size="sm" variant="outline" onClick={() => void markReadMutation.mutateAsync(item.id)}>
                          Mark read
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Session toasts</p>
            {items.length === 0 ? (
            <p className="rounded-xl border border-border/60 p-4 text-sm text-muted-foreground">No notifications yet.</p>
          ) : (
            items.map((item) => (
              <div key={item.id} className="rounded-xl border border-border/70 bg-card/70 p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium">{item.title}</p>
                  <span className="text-xs text-muted-foreground">{formatTime(item.createdAt)}</span>
                </div>
                {item.description ? <p className="mt-1 text-xs text-muted-foreground">{item.description}</p> : null}
              </div>
            ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
