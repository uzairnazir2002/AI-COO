"use client";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ReauthActionDialog({
  open,
  onOpenChange,
  title,
  description,
  password,
  onPasswordChange,
  mfaCode,
  onMfaCodeChange,
  onSubmit,
  busy = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  password: string;
  onPasswordChange: (value: string) => void;
  mfaCode: string;
  onMfaCodeChange: (value: string) => void;
  onSubmit: () => Promise<void>;
  busy?: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            type="password"
            placeholder="Current password"
            value={password}
            onChange={(event) => onPasswordChange(event.target.value)}
          />
          <Input
            placeholder="MFA code (optional)"
            value={mfaCode}
            onChange={(event) => onMfaCodeChange(event.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button
            disabled={busy}
            onClick={async () => {
              await onSubmit();
              onOpenChange(false);
            }}
          >
            {busy ? "Authorizing..." : "Authorize"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

