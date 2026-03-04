"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

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
      <div>
        <h1 className="text-2xl font-semibold">Organizations</h1>
        <p className="text-sm text-muted-foreground">Select or create an organization workspace.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Your organizations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {orgs.length === 0 ? <p className="text-sm text-muted-foreground">No organizations yet.</p> : null}
          {orgs.map((org) => (
            <div key={org.org_id} className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="font-medium">{org.name}</p>
                <p className="text-xs text-muted-foreground">{org.role}</p>
              </div>
              <Button
                onClick={() => {
                  setSelectedOrgId(org.org_id);
                  router.push("/app/dashboard");
                }}
                size="sm"
              >
                Open
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
          <form
            className="flex flex-col gap-3 md:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError("");
              try {
                const created = await createOrg.mutateAsync(name);
                setSelectedOrgId(created.org_id);
                router.push("/app/dashboard");
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
