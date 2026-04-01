"use client";

import type { FormEvent } from "react";
import { ArrowRight, Building2, CheckCircle2 } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { TabNav } from "@/components/layout/tab-nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Org } from "@/types/domain";

export function OrgsWorkspaceContainer({
  activeTab,
  onTabChange,
  orgs,
  onOpenOrg,
  name,
  onNameChange,
  onCreate,
  creating,
  error,
  successMessage,
}: {
  activeTab: string;
  onTabChange: (tab: string) => void;
  orgs: Org[];
  onOpenOrg: (orgId: string) => void;
  name: string;
  onNameChange: (value: string) => void;
  onCreate: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  creating: boolean;
  error: string;
  successMessage: string;
}) {
  return (
    <>
      <TabNav
        active={activeTab}
        onChange={onTabChange}
        items={[
          { id: "organizations", label: "Organizations" },
          { id: "create", label: "Create" },
        ]}
      />

      {activeTab === "organizations" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Your organizations</h2>
            </PanelHeader>
            <PanelBody className="space-y-3">
              {orgs.length === 0 ? (
                <EmptyState
                  eyebrow="First-time setup"
                  title="Create your first organization."
                  description="New accounts without organizations are routed here automatically. Once created, you will land on the dashboard with onboarding prompts."
                />
              ) : null}
              {orgs.length > 0 ? (
                <SuccessStateCard
                  title="Organization context is active"
                  description="Selecting an organization scopes every API call, permission check, and report in the app."
                />
              ) : null}
              {orgs.map((org) => (
                <div key={org.org_id} className="flex items-center justify-between rounded-[22px] border border-border/70 bg-card/70 p-4">
                  <div>
                    <p className="font-medium">{org.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{org.role}</p>
                  </div>
                  <Button onClick={() => onOpenOrg(org.org_id)} size="sm">
                    Open <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              ))}
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      {activeTab === "create" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Create organization</h2>
              <p className="text-sm text-muted-foreground">Owner role is assigned to your account.</p>
            </PanelHeader>
            <PanelBody>
              <div className="mb-4 rounded-[22px] border border-border/70 bg-card/70 p-4 text-xs text-muted-foreground">
                New organizations create an isolated `org_id` scope. Data, alerts, reports, and RBAC policies remain partitioned by organization.
              </div>
              <div className="mb-5 grid gap-3 md:grid-cols-3">
                {[
                  { icon: Building2, title: "Workspace", text: "Each organization keeps its own financial context." },
                  { icon: CheckCircle2, title: "RBAC", text: "You start as owner with full controls." },
                  { icon: ArrowRight, title: "Next step", text: "After creation, go straight into dashboard onboarding." },
                ].map((item) => (
                  <div key={item.title} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <item.icon className="h-4 w-4 text-primary" />
                    <p className="mt-3 text-sm font-medium">{item.title}</p>
                    <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.text}</p>
                  </div>
                ))}
              </div>
              <form className="flex flex-col gap-3 md:flex-row" onSubmit={(e) => void onCreate(e)}>
                <Input value={name} onChange={(e) => onNameChange(e.target.value)} placeholder="Acme LLC" required />
                <Button disabled={creating}>Create</Button>
              </form>
              {error ? <InlineErrorBanner className="mt-3" message={error} /> : null}
              {successMessage ? (
                <div className="mt-3">
                  <SuccessStateCard title="Organization created" description={successMessage} />
                </div>
              ) : null}
            </PanelBody>
          </Panel>
        </section>
      ) : null}
    </>
  );
}
