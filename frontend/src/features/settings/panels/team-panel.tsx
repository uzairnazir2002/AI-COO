"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Role } from "@/types/domain";

type MemberView = {
  user_id: string;
  email: string;
  role: Role;
};

export function TeamPanel({
  role,
  email,
  setEmail,
  inviteRole,
  setInviteRole,
  invitePending,
  onInvite,
  members,
  roleDescriptions,
}: {
  role?: Role;
  email: string;
  setEmail: (value: string) => void;
  inviteRole: Role;
  setInviteRole: (role: Role) => void;
  invitePending: boolean;
  onInvite: () => Promise<void>;
  members: MemberView[];
  roleDescriptions: Record<Role, string>;
}) {
  const owner = role === "OWNER";

  return (
    <section id="settings-team" className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Members</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!owner ? <p className="text-sm text-muted-foreground">Only owners can view and invite members.</p> : null}

          {owner ? (
            <form
              className="flex flex-wrap gap-2"
              onSubmit={async (event) => {
                event.preventDefault();
                await onInvite();
              }}
            >
              <Input
                type="email"
                placeholder="member@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="max-w-xs"
              />
              <div className="w-40">
                <Select value={inviteRole} onValueChange={(value) => setInviteRole(value as Role)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="VIEWER">Viewer</SelectItem>
                    <SelectItem value="EDITOR">Editor</SelectItem>
                    <SelectItem value="OWNER">Owner</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button disabled={invitePending} type="submit">Invite</Button>
            </form>
          ) : null}

          <div className="space-y-2">
            {members.map((member) => (
              <div key={member.user_id} className="flex items-center justify-between rounded-[22px] border border-border/70 bg-card/70 p-4">
                <div>
                  <p className="font-medium">{member.email}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{roleDescriptions[member.role]}</p>
                </div>
                <Badge>{member.role}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

