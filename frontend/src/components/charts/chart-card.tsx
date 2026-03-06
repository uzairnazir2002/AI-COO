import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ChartCard({
  title,
  description,
  loading,
  empty,
  actions,
  children,
}: {
  title: string;
  description?: string;
  loading?: boolean;
  empty?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {actions}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-72 w-full rounded-2xl" /> : null}
        {!loading && empty ? empty : null}
        {!loading && !empty ? children : null}
      </CardContent>
    </Card>
  );
}
