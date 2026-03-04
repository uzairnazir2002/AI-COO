"use client";

import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useToast } from "@/components/common/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useForecast, useForecastOverride } from "@/features/forecast/hooks";
import { formatMoney } from "@/lib/utils/format";

type DraftRow = {
  revenue: string;
  expense: string;
};

export default function ForecastPage() {
  const [months, setMonths] = useState<3 | 6>(6);
  const [scenario, setScenario] = useState<"base" | "high" | "low">("base");
  const [drafts, setDrafts] = useState<Record<string, DraftRow>>({});

  const toast = useToast();
  const forecast = useForecast(months);
  const override = useForecastOverride();

  const points = useMemo(() => {
    const arr = forecast.data?.scenarios[scenario] ?? [];
    return arr.map((item) => ({
      ...item,
      revenue_pred: Number(item.revenue_pred),
      expense_pred: Number(item.expense_pred),
      confidence_low: Number(item.confidence_low),
      confidence_high: Number(item.confidence_high),
    }));
  }, [forecast.data, scenario]);

  const risk = points.length > 1 && points[points.length - 1].expense_pred > points[points.length - 1].revenue_pred;

  async function saveDraft(month: string) {
    const row = drafts[month];
    if (!row) return;
    await override.mutateAsync({
      month,
      scenario: scenario.toUpperCase() as "BASE" | "HIGH" | "LOW",
      revenue_override: row.revenue.trim() ? Number(row.revenue) : undefined,
      expense_override: row.expense.trim() ? Number(row.expense) : undefined,
    });
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[month];
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="mr-auto text-2xl font-semibold">Forecast</h1>
        <div className="w-24">
          <Select value={String(months)} onValueChange={(value) => setMonths(Number(value) as 3 | 6)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="3">3 mo</SelectItem>
              <SelectItem value="6">6 mo</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-32">
          <Select value={scenario} onValueChange={(value) => setScenario(value as "base" | "high" | "low")}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="base">Base</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {risk ? <p className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-warning">Risk indicator: projected expenses exceed revenue in outer horizon.</p> : null}

      <Card>
        <CardHeader><CardTitle>Scenario Projection</CardTitle></CardHeader>
        <CardContent>
          <div className="h-80 w-full">
            <ResponsiveContainer>
              <AreaChart data={points}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area dataKey="confidence_low" fill="#bfdbfe" stroke="#93c5fd" fillOpacity={0.22} name="Confidence low" />
                <Area dataKey="confidence_high" fill="#93c5fd" stroke="#60a5fa" fillOpacity={0.14} name="Confidence high" />
                <Line dataKey="revenue_pred" stroke="#2563eb" strokeWidth={2} name="Revenue" />
                <Line dataKey="expense_pred" stroke="#dc2626" strokeWidth={2} name="Expense" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Override Editor</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <p data-testid="forecast-dirty-count" className="text-sm text-muted-foreground">Dirty rows: {Object.keys(drafts).length}</p>
            <Button
              data-testid="forecast-save-all"
              variant="outline"
              disabled={Object.keys(drafts).length === 0 || override.isPending}
              onClick={async () => {
                for (const month of Object.keys(drafts)) {
                  await saveDraft(month);
                }
                toast.toast({ title: "All overrides saved" });
              }}
            >
              Save All
            </Button>
            <Button data-testid="forecast-reset-all" variant="ghost" disabled={Object.keys(drafts).length === 0} onClick={() => setDrafts({})}>Reset All</Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1">Month</th>
                  <th className="py-1">Revenue (model)</th>
                  <th className="py-1">Expense (model)</th>
                  <th className="py-1">Revenue override</th>
                  <th className="py-1">Expense override</th>
                  <th className="py-1">Confidence</th>
                  <th className="py-1">Actions</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p) => {
                  const draft = drafts[p.month] ?? { revenue: "", expense: "" };
                  const isDirty = Boolean(drafts[p.month]);
                  return (
                    <tr key={p.month} className="border-t">
                      <td className="py-2 font-medium">{p.month}</td>
                      <td>{formatMoney(p.revenue_pred)}</td>
                      <td>{formatMoney(p.expense_pred)}</td>
                      <td>
                        <Input
                          data-testid={`forecast-override-revenue-${p.month}`}
                          value={draft.revenue}
                          placeholder="leave empty"
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [p.month]: { ...draft, revenue: e.target.value },
                            }))
                          }
                        />
                      </td>
                      <td>
                        <Input
                          data-testid={`forecast-override-expense-${p.month}`}
                          value={draft.expense}
                          placeholder="leave empty"
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [p.month]: { ...draft, expense: e.target.value },
                            }))
                          }
                        />
                      </td>
                      <td>{formatMoney(p.confidence_low)} - {formatMoney(p.confidence_high)}</td>
                      <td>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`forecast-save-${p.month}`}
                            size="sm"
                            disabled={!isDirty || override.isPending}
                            onClick={async () => {
                              await saveDraft(p.month);
                              toast.toast({ title: `Override saved for ${p.month}` });
                            }}
                          >
                            Save
                          </Button>
                          <Button
                            data-testid={`forecast-reset-${p.month}`}
                            size="sm"
                            variant="outline"
                            disabled={!isDirty}
                            onClick={() => {
                              setDrafts((prev) => {
                                const next = { ...prev };
                                delete next[p.month];
                                return next;
                              });
                            }}
                          >
                            Reset
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
