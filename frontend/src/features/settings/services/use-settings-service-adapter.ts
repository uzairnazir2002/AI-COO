"use client";

import type { Role } from "@/types/domain";
import { useToast } from "@/components/common/use-toast";
import { useInviteMember, useRequestAccountDeletion, useRequestOrgDeletion } from "@/features/settings/hooks";

export function useSettingsServiceAdapter() {
  const toast = useToast();
  const invite = useInviteMember();
  const requestAccountDeletion = useRequestAccountDeletion();
  const requestOrgDeletion = useRequestOrgDeletion();

  return {
    invitePending: invite.isPending,
    requestAccountDeletionPending: requestAccountDeletion.isPending,
    requestOrgDeletionPending: requestOrgDeletion.isPending,
    inviteMember: async (email: string, role: Role, reauthToken?: string) => {
      const result = await invite.mutateAsync({ email, role, reauthToken });
      toast.toast({
        title: "Invite created",
        description: result.invite_token ? `/auth/register?invite_token=${result.invite_token}` : "Invite sent",
      });
      return result;
    },
    requestAccountDeletionAction: async (reason?: string) => {
      const result = await requestAccountDeletion.mutateAsync({ reason: reason || undefined });
      toast.toast({
        title: "Account deletion requested",
        description: `Request ${result.request_id} queued for ${result.delete_after}.`,
        variant: "warning",
      });
      return result;
    },
    requestOrgDeletionAction: async (reason: string | undefined, reauthToken?: string) => {
      const result = await requestOrgDeletion.mutateAsync({
        reason: reason || undefined,
        reauthToken,
      });
      toast.toast({
        title: "Organization deletion requested",
        description: `Request ${result.request_id} queued for ${result.delete_after}.`,
        variant: "warning",
      });
      return result;
    },
  };
}

