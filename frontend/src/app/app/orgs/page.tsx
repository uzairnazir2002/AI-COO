"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { SectionHeader } from "@/components/common/section-header";
import { StatusStrip } from "@/components/layout/status-strip";
import { useCreateOrg } from "@/features/orgs/hooks";
import { OrgsWorkspaceContainer } from "@/features/orgs/containers/orgs-workspace-container";
import { useAppStore } from "@/store/appStore";

export default function OrgsPage() {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [activeTab, setActiveTab] = useState("organizations");
  const router = useRouter();
  const createOrg = useCreateOrg();
  const orgs = useAppStore((s) => s.orgs);
  const selectedOrgId = useAppStore((s) => s.selectedOrgId);
  const setSelectedOrgId = useAppStore((s) => s.setSelectedOrgId);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Organizations"
        description="Your selected organization persists across sessions and scopes every query, permission check, and report flow."
      />

      <StatusStrip
        items={[
          { label: "Organizations", value: String(orgs.length), tone: "neutral" },
          { label: "Selected", value: selectedOrgId || "None", tone: "neutral" },
        ]}
      />

      <OrgsWorkspaceContainer
        activeTab={activeTab}
        onTabChange={setActiveTab}
        orgs={orgs}
        onOpenOrg={(orgId) => {
          setSelectedOrgId(orgId);
          router.push("/app/dashboard");
        }}
        name={name}
        onNameChange={setName}
        onCreate={async (e) => {
          e.preventDefault();
          setError("");
          setSuccessMessage("");
          try {
            const created = await createOrg.mutateAsync(name);
            setSuccessMessage(`Created ${created.name}. Redirecting to onboarding...`);
            setSelectedOrgId(created.org_id);
            router.push("/app/onboarding");
          } catch (err) {
            setError(err instanceof Error ? err.message : "Failed");
          }
        }}
        creating={createOrg.isPending}
        error={error}
        successMessage={successMessage}
      />
    </div>
  );
}

