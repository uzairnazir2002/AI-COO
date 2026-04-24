"use client";

import Link from "next/link";
import { BarChart3, Building2, CalendarDays, ClipboardList, CreditCard, Megaphone, Plane, Users } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/appStore";

export default function WorkforceLandingPage() {
  const orgId = useAppStore((s) => s.selectedOrgId);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Workforce"
        title="Select an organization to manage workforce."
        description="Workforce is fully org-scoped. Choose an organization from the header to view employees, departments, and job titles."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Workforce operations"
        description="Employee directory and org structure in one place."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Link href="/app/dashboard" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Intelligence snapshot</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Cross-cutting workforce signals on the executive dashboard.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Today&apos;s attendance, leave backlog, payroll due, contract/probation windows, and announcement ack gaps—the
              same signals the AI assistant grounds on. For a downloadable range summary, open Reports and use the Workforce
              intelligence section (<span className="font-mono text-xs text-foreground">#workforce-summary</span>).
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/workforce/employees" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <Users className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Employees</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Search, view, and manage employees.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Directory, profiles, manager relationships, and basic compensation fields (role-safe).
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/settings?tab=workforce" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <Building2 className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Departments & titles</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Maintain org structure.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Configure departments and job titles used across workforce workflows.
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/workforce/attendance" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <CalendarDays className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Attendance</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Daily log, calendar, shifts, and corrections.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Clock in/out, manual attendance entries, lateness detection, and correction approvals.
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/workforce/leave" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <Plane className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Leave</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Requests, approvals, balances, and calendar.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Track leave types and balances, approve requests, and keep attendance aligned with leave days.
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/workforce/communications" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <Megaphone className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Communications</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Announcements and org messaging.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Announcements, delivery log, and optional payroll/leave automations. Manage reusable titles and bodies in the template library.
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/workforce/payroll" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <CreditCard className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>Payroll</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Periods, drafts, approvals, payslips, exports.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Drafts from attendance, salaried unpaid-leave deduction, adjustments, CSV/PDF export, approve; owners mark paid.
            </CardContent>
          </Card>
        </Link>

        <Link href="/app/workforce/hr" className="group">
          <Card className="h-full transition hover:border-primary/30 hover:shadow-md">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                <ClipboardList className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <CardTitle>HR admin</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Onboarding, policies, documents.</p>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Checklists for onboarding/offboarding, policy acknowledgements, and employee documents.
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}

