"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Building2, CheckCircle2 } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateOrg } from "@/features/orgs/hooks";
import { useAppStore } from "@/store/appStore";

export default function OrgsPage() {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();
  const createOrg = useCreateOrg();
  const orgs = useAppStore((s) => s.orgs);
  const setSelectedOrgId = useAppStore((s) => s.setSelectedOrgId);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Organizations"
        description="Your selected organization persists across sessions and scopes every query, permission check, and report flow."
      />

      <Card>
        <CardHeader>
          <CardTitle>Your organizations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {orgs.length === 0 ? (
            <EmptyState
              eyebrow="First-time setup"
              title="Create your first organization."
              description="New accounts without organizations are routed here automatically. Once created, you’ll land on the dashboard with onboarding prompts."
            />
          ) : null}
          {orgs.map((org) => (
            <div key={org.org_id} className="flex items-center justify-between rounded-[22px] border border-border/70 bg-card/70 p-4">
              <div>
                <p className="font-medium">{org.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{org.role}</p>
              </div>
              <Button
                onClick={() => {
                  setSelectedOrgId(org.org_id);
                  router.push("/app/dashboard");
                }}
                size="sm"
              >
                Open <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Create organization</CardTitle>
          <CardDescription>Owner role is assigned to your account.</CardDescription>
        </CardHeader>
        <CardContent>
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
          <form
            className="flex flex-col gap-3 md:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError("");
              try {
                const created = await createOrg.mutateAsync(name);
                setSelectedOrgId(created.org_id);
                router.push("/app/onboarding");
              } catch (err) {
                setError(err instanceof Error ? err.message : "Failed");
              }
            }}
          >
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme LLC" required />
            <Button disabled={createOrg.isPending}>Create</Button>
          </form>
          {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
