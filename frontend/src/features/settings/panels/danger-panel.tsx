"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DangerPanel() {
  return (
    <section id="settings-danger" className="space-y-3">
      <Card className="border-danger/30">
        <CardHeader><CardTitle>Danger Zone</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Organization deletion controls remain in the Data & compliance actions section above and still require explicit confirmation and re-auth.
          </p>
        </CardContent>
      </Card>
    </section>
  );
}

