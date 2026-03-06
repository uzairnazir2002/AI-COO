import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type Summary = {
  headline: string;
  highlights: string[];
  risks: string[];
  actions: string[];
  confidence: string;
};

export function AIInsightPanel({ summary, fallbackUsed }: { summary: Summary | null; fallbackUsed?: boolean }) {
  if (!summary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>AI Executive Summary</CardTitle>
          <CardDescription>Based strictly on computed metrics</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">No summary yet.</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>AI Executive Summary</CardTitle>
          <div className="flex gap-2">
            <Badge>{summary.confidence}</Badge>
            {fallbackUsed ? <Badge variant="warning">Fallback</Badge> : null}
          </div>
        </div>
        <CardDescription>Based strictly on computed metrics</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="rounded-2xl border border-primary/15 bg-primary/5 p-4 font-medium">{summary.headline}</p>
        <div>
          <p className="font-medium">Highlights</p>
          <ul className="list-disc pl-5 text-muted-foreground">
            {summary.highlights.map((line) => <li key={line}>{line}</li>)}
          </ul>
        </div>
        <div>
          <p className="font-medium">Risks</p>
          <ul className="list-disc pl-5 text-muted-foreground">
            {summary.risks.map((line) => <li key={line}>{line}</li>)}
          </ul>
        </div>
        <div>
          <p className="font-medium">Actions</p>
          <ul className="list-disc pl-5 text-muted-foreground">
            {summary.actions.map((line) => <li key={line}>{line}</li>)}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
