"use client";

import { Mail } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDate } from "@/lib/utils/format";
import type { BeatScheduleItem, Job, OutboxEvent } from "@/types/domain";

export function OutboxTabPanel({
  isOwner,
  outboxStatus,
  setOutboxStatus,
  outboxCountsByStatus,
  outboxItems,
  outboxTotal,
  outboxPage,
  outboxPageSize,
  onPrevOutboxPage,
  onNextOutboxPage,
  retryOutboxPending,
  onRetryOutboxEvent,
  scheduler,
  systemJobs,
  onResumeSchedule,
  onPauseSchedule,
  onRunSchedule,
}: {
  isOwner: boolean;
  outboxStatus: string;
  setOutboxStatus: (value: string) => void;
  outboxCountsByStatus: Record<string, number>;
  outboxItems: OutboxEvent[];
  outboxTotal: number;
  outboxPage: number;
  outboxPageSize: number;
  onPrevOutboxPage: () => void;
  onNextOutboxPage: () => void;
  retryOutboxPending: boolean;
  onRetryOutboxEvent: (eventId: string) => Promise<void>;
  scheduler: BeatScheduleItem[];
  systemJobs: Job[];
  onResumeSchedule: (name: string) => Promise<void>;
  onPauseSchedule: (name: string) => Promise<void>;
  onRunSchedule: (name: string) => Promise<void>;
}) {
  if (!isOwner) return null;

  return (
    <section id="activity-outbox" className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Outbox monitor</CardTitle>
            <CardDescription>Owner-only visibility into queued, retrying, failed, and sent org email events.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="w-40">
                <Select value={outboxStatus} onValueChange={setOutboxStatus}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All statuses</SelectItem>
                    <SelectItem value="PENDING">Pending</SelectItem>
                    <SelectItem value="PROCESSING">Processing</SelectItem>
                    <SelectItem value="RETRYING">Retrying</SelectItem>
                    <SelectItem value="FAILED">Failed</SelectItem>
                    <SelectItem value="SENT">Sent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {Object.entries(outboxCountsByStatus).map(([key, value]) => (
                <Badge key={key} variant={key === "FAILED" ? "destructive" : key === "RETRYING" ? "warning" : "secondary"}>
                  {key}: {value}
                </Badge>
              ))}
            </div>

            {outboxItems.length === 0 ? (
              <p className="text-sm text-muted-foreground">No outbox events for the selected organization and filter.</p>
            ) : (
              outboxItems.map((event) => (
                <div key={event.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-primary/10 p-2 text-primary">
                        <Mail className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-medium">{event.event_type}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Created {formatDate(event.created_at)} | Attempts {event.attempts}/{event.max_attempts}
                        </p>
                      </div>
                    </div>
                    <Badge variant={event.status === "FAILED" ? "destructive" : event.status === "RETRYING" ? "warning" : event.status === "SENT" ? "success" : "secondary"}>
                      {event.status}
                    </Badge>
                  </div>
                  <pre className="mt-4 overflow-auto rounded-[18px] border border-border/60 bg-background/65 p-3 text-xs">
                    {JSON.stringify(event.payload ?? {}, null, 2)}
                  </pre>
                  {event.last_error ? <p className="mt-3 text-xs text-danger">{event.last_error}</p> : null}
                  {["FAILED", "RETRYING"].includes(event.status) ? (
                    <div className="mt-3 flex justify-end">
                      <Button variant="outline" size="sm" disabled={retryOutboxPending} onClick={() => void onRetryOutboxEvent(event.id)}>
                        Retry delivery
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))
            )}

            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">{outboxTotal} total outbox events</p>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={outboxPage <= 1} onClick={onPrevOutboxPage}>
                  Prev
                </Button>
                <span className="text-sm">Page {outboxPage}</span>
                <Button variant="outline" size="sm" disabled={Boolean(outboxPage * outboxPageSize >= outboxTotal)} onClick={onNextOutboxPage}>
                  Next
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Scheduler admin</CardTitle>
            <CardDescription>Configured beat schedule plus recent system-wide worker jobs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {scheduler.map((entry) => (
                <div key={entry.name} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{entry.name}</p>
                    <Badge variant={entry.paused ? "warning" : "outline"}>{entry.paused ? "Paused" : "Scheduled"}</Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{entry.task}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{entry.schedule}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {entry.paused ? (
                      <Button size="sm" variant="outline" onClick={() => void onResumeSchedule(entry.name)}>
                        Resume
                      </Button>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => void onPauseSchedule(entry.name)}>
                        Pause
                      </Button>
                    )}
                    <Button size="sm" variant="outline" onClick={() => void onRunSchedule(entry.name)}>
                      Run now
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-xs uppercase text-muted-foreground">Recent system jobs</p>
              <div className="mt-3 space-y-3">
                {systemJobs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No system-scoped worker jobs tracked yet.</p>
                ) : (
                  systemJobs.map((job) => (
                    <div key={job.id} className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium">{job.task_name}</p>
                        <Badge variant={job.status === "FAILED" ? "destructive" : job.status === "SUCCEEDED" ? "success" : "secondary"}>
                          {job.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">Updated {formatDate(job.updated_at)}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

