"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api, apiFetchRaw } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import {
  workforceAttendanceCalendarSchema,
  workforceAttendanceCorrectionSchema,
  workforceAttendanceDailySchema,
  workforceDepartmentSchema,
  workforceEmployeeSchema,
  workforceAnnouncementAttachmentUploadSchema,
  workforceAnnouncementDeliveryListSchema,
  workforceAnnouncementReceiptSchema,
  workforceAnnouncementSchema,
  workforceAnnouncementTemplateSchema,
  workforceAutomationKeysSchema,
  workforceLeaveBalanceSchema,
  workforceLeaveRequestSchema,
  workforceLeaveTypeSchema,
  workforcePayrollAdjustmentSchema,
  workforcePayrollEntrySchema,
  workforcePayrollPeriodSchema,
  workforcePayslipPreviewSchema,
  workforceShiftAssignmentSchema,
  workforceShiftSchema,
  workforceTitleSchema,
} from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type {
  WorkforceAttendanceCalendar,
  WorkforceAttendanceCorrection,
  WorkforceAttendanceDaily,
  WorkforceAnnouncement,
  WorkforceAnnouncementDelivery,
  WorkforceAnnouncementDeliveryList,
  WorkforceAnnouncementTemplate,
  WorkforceDepartment,
  WorkforceEmployee,
  WorkforceLeaveBalance,
  WorkforceLeaveRequest,
  WorkforceLeaveType,
  WorkforcePayrollAdjustment,
  WorkforcePayrollEntry,
  WorkforcePayrollPeriod,
  WorkforcePayslipPreview,
  WorkforceShift,
  WorkforceShiftAssignment,
  WorkforceTitle,
} from "@/types/domain";

function requireOrgId(orgId: string | null, message = "Select an organization before continuing."): string {
  if (!orgId) throw new ApiError(message, 400);
  return orgId;
}

function requireEditor(orgId: string | null, role: string | undefined, message = "Only editors or owners can perform this action."): string {
  const resolved = requireOrgId(orgId, message);
  if (role !== "OWNER" && role !== "EDITOR") throw new ApiError(message, 403);
  return resolved;
}

function requireOwner(orgId: string | null, role: string | undefined, message = "Only owners can perform this action."): string {
  const resolved = requireOrgId(orgId, message);
  if (role !== "OWNER") throw new ApiError(message, 403);
  return resolved;
}

export function useWorkforceDepartments(includeInactive = true) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceDepartments(orgId || "", includeInactive),
    queryFn: async () => {
      const out = await api<WorkforceDepartment[]>(
        `${apiPaths.workforceDepartments}?org_id=${orgId}&include_inactive=${includeInactive ? "true" : "false"}`,
      );
      return out.map((row) => workforceDepartmentSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforceDepartment() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; code?: string | null; is_active?: boolean }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create departments.");
      const out = await api<WorkforceDepartment>(apiPaths.workforceDepartments, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name,
          code: payload.code ?? null,
          is_active: payload.is_active ?? true,
        }),
      });
      return workforceDepartmentSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceDepartments", orgId || ""] }),
  });
}

export function useUpdateWorkforceDepartment() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; name?: string | null; code?: string | null; is_active?: boolean | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update departments.");
      const out = await api<WorkforceDepartment>(apiPaths.workforceDepartmentById(payload.id), {
        method: "PUT",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name ?? null,
          code: payload.code ?? null,
          is_active: payload.is_active ?? null,
        }),
      });
      return workforceDepartmentSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceDepartments", orgId || ""] }),
  });
}

export function useDeactivateWorkforceDepartment() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot deactivate departments.");
      return api<{ ok: boolean }>(`${apiPaths.workforceDepartmentById(id)}?org_id=${resolved}`, { method: "DELETE" });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceDepartments", orgId || ""] }),
  });
}

export function useWorkforceTitles(includeInactive = true) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceTitles(orgId || "", includeInactive),
    queryFn: async () => {
      const out = await api<WorkforceTitle[]>(
        `${apiPaths.workforceTitles}?org_id=${orgId}&include_inactive=${includeInactive ? "true" : "false"}`,
      );
      return out.map((row) => workforceTitleSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforceTitle() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; level?: number | null; is_active?: boolean }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create titles.");
      const out = await api<WorkforceTitle>(apiPaths.workforceTitles, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name,
          level: payload.level ?? null,
          is_active: payload.is_active ?? true,
        }),
      });
      return workforceTitleSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceTitles", orgId || ""] }),
  });
}

export function useUpdateWorkforceTitle() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; name?: string | null; level?: number | null; is_active?: boolean | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update titles.");
      const out = await api<WorkforceTitle>(apiPaths.workforceTitleById(payload.id), {
        method: "PUT",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name ?? null,
          level: payload.level ?? null,
          is_active: payload.is_active ?? null,
        }),
      });
      return workforceTitleSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceTitles", orgId || ""] }),
  });
}

export function useDeactivateWorkforceTitle() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot deactivate titles.");
      return api<{ ok: boolean }>(`${apiPaths.workforceTitleById(id)}?org_id=${resolved}`, { method: "DELETE" });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceTitles", orgId || ""] }),
  });
}

type EmployeeQueryParams = {
  q?: string;
  department_id?: string;
  title_id?: string;
  manager_employee_id?: string;
  employment_status?: string;
  include_inactive?: boolean;
  limit?: number;
};

export function useWorkforceEmployees(params: EmployeeQueryParams) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceEmployees(orgId || "", params),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      if (params.q) qs.set("q", params.q);
      if (params.department_id) qs.set("department_id", params.department_id);
      if (params.title_id) qs.set("title_id", params.title_id);
      if (params.manager_employee_id) qs.set("manager_employee_id", params.manager_employee_id);
      if (params.employment_status) qs.set("employment_status", params.employment_status);
      if (params.include_inactive) qs.set("include_inactive", "true");
      if (params.limit) qs.set("limit", String(params.limit));
      const out = await api<WorkforceEmployee[]>(`${apiPaths.workforceEmployees}?${qs.toString()}`);
      return out.map((row) => workforceEmployeeSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useWorkforceEmployee(employeeId: string) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceEmployee(orgId || "", employeeId),
    queryFn: async () => {
      const out = await api<WorkforceEmployee>(`${apiPaths.workforceEmployeeById(employeeId)}?org_id=${orgId}`);
      return workforceEmployeeSchema.parse(out);
    },
    enabled: Boolean(orgId && employeeId),
  });
}

export function useCreateWorkforceEmployee() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<WorkforceEmployee> & { first_name: string; last_name: string }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create employees.");
      const out = await api<WorkforceEmployee>(apiPaths.workforceEmployees, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          employee_code: payload.employee_code ?? null,
          first_name: payload.first_name,
          last_name: payload.last_name,
          email: payload.email ?? null,
          phone: payload.phone ?? null,
          department_id: payload.department_id ?? null,
          title_id: payload.title_id ?? null,
          manager_employee_id: payload.manager_employee_id ?? null,
          location_id: payload.location_id ?? null,
          employment_type: payload.employment_type ?? "FULL_TIME",
          employment_status: payload.employment_status ?? "ACTIVE",
          start_date: payload.start_date ?? null,
          end_date: payload.end_date ?? null,
          salary_type: payload.salary_type ?? "SALARIED",
          base_salary: payload.base_salary ?? null,
          hourly_rate: payload.hourly_rate ?? null,
          is_active: payload.is_active ?? true,
        }),
      });
      return workforceEmployeeSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceEmployees", orgId || ""] }),
  });
}

export function useUpdateWorkforceEmployee() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string } & Partial<WorkforceEmployee>) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update employees.");
      const body: Record<string, unknown> = { org_id: resolved };
      for (const key of [
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "phone",
        "department_id",
        "title_id",
        "manager_employee_id",
        "location_id",
        "employment_type",
        "employment_status",
        "start_date",
        "end_date",
        "salary_type",
        "base_salary",
        "hourly_rate",
        "is_active",
      ] as const) {
        if (key in payload) body[key] = (payload as Record<string, unknown>)[key] ?? null;
      }
      const out = await api<WorkforceEmployee>(apiPaths.workforceEmployeeById(payload.id), {
        method: "PUT",
        body: JSON.stringify(body),
      });
      return workforceEmployeeSchema.parse(out);
    },
    onSuccess: async (_data, variables) => {
      await qc.invalidateQueries({ queryKey: ["workforceEmployees", orgId || ""] });
      await qc.invalidateQueries({ queryKey: qk.workforceEmployee(orgId || "", variables.id) });
    },
  });
}

export function useDeactivateWorkforceEmployee() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireOwner(orgId, role, "Only owners can deactivate employees.");
      return api<{ ok: boolean }>(`${apiPaths.workforceEmployeeById(id)}?org_id=${resolved}`, { method: "DELETE" });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceEmployees", orgId || ""] }),
  });
}

export function useWorkforceShifts(includeInactive = true) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceShifts(orgId || "", includeInactive),
    queryFn: async () => {
      const out = await api<WorkforceShift[]>(
        `${apiPaths.workforceShifts}?org_id=${orgId}&include_inactive=${includeInactive ? "true" : "false"}`,
      );
      return out.map((row) => workforceShiftSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforceShift() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; start_time: string; end_time: string; grace_minutes?: number; is_active?: boolean }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create shifts.");
      const out = await api<WorkforceShift>(apiPaths.workforceShifts, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name,
          start_time: payload.start_time,
          end_time: payload.end_time,
          grace_minutes: payload.grace_minutes ?? 5,
          is_active: payload.is_active ?? true,
        }),
      });
      return workforceShiftSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceShifts", orgId || ""] }),
  });
}

export function useUpdateWorkforceShift() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; name?: string | null; start_time?: string | null; end_time?: string | null; grace_minutes?: number | null; is_active?: boolean | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update shifts.");
      const out = await api<WorkforceShift>(apiPaths.workforceShiftById(payload.id), {
        method: "PUT",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name ?? null,
          start_time: payload.start_time ?? null,
          end_time: payload.end_time ?? null,
          grace_minutes: payload.grace_minutes ?? null,
          is_active: payload.is_active ?? null,
        }),
      });
      return workforceShiftSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceShifts", orgId || ""] }),
  });
}

export function useDeactivateWorkforceShift() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot deactivate shifts.");
      return api<{ ok: boolean }>(`${apiPaths.workforceShiftById(id)}?org_id=${resolved}`, { method: "DELETE" });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceShifts", orgId || ""] }),
  });
}

export function useWorkforceShiftAssignments(params: { employee_id?: string; shift_id?: string; as_of?: string; limit?: number }) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceShiftAssignments(orgId || "", params),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      if (params.employee_id) qs.set("employee_id", params.employee_id);
      if (params.shift_id) qs.set("shift_id", params.shift_id);
      if (params.as_of) qs.set("as_of", params.as_of);
      if (params.limit) qs.set("limit", String(params.limit));
      const out = await api<WorkforceShiftAssignment[]>(`${apiPaths.workforceShiftAssignments}?${qs.toString()}`);
      return out.map((row) => workforceShiftAssignmentSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforceShiftAssignment() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { employee_id: string; shift_id: string; effective_from: string; effective_to?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot assign shifts.");
      const out = await api<WorkforceShiftAssignment>(apiPaths.workforceShiftAssignments, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          employee_id: payload.employee_id,
          shift_id: payload.shift_id,
          effective_from: payload.effective_from,
          effective_to: payload.effective_to ?? null,
        }),
      });
      return workforceShiftAssignmentSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceShiftAssignments", orgId || ""] }),
  });
}

export function useWorkforceAttendanceDaily(day: string, employeeId?: string) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceAttendanceDaily(orgId || "", day, employeeId || ""),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "", date: day });
      if (employeeId) qs.set("employee_id", employeeId);
      const out = await api<WorkforceAttendanceDaily>(`${apiPaths.workforceAttendanceDaily}?${qs.toString()}`, {
        schema: workforceAttendanceDailySchema,
      });
      return workforceAttendanceDailySchema.parse(out);
    },
    enabled: Boolean(orgId && day),
  });
}

export function useWorkforceAttendanceCalendar(month: string) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceAttendanceCalendar(orgId || "", month),
    queryFn: async () => {
      const out = await api<WorkforceAttendanceCalendar>(`${apiPaths.workforceAttendanceCalendar}?org_id=${orgId}&month=${encodeURIComponent(month)}`, {
        schema: workforceAttendanceCalendarSchema,
      });
      return workforceAttendanceCalendarSchema.parse(out);
    },
    enabled: Boolean(orgId && month),
  });
}

export function useClockIn() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { employee_id: string; at?: string }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot clock in/out.");
      return api(apiPaths.workforceAttendanceClockIn, {
        method: "POST",
        body: JSON.stringify({ org_id: resolved, employee_id: payload.employee_id, at: payload.at ?? null }),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceDaily", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceCalendar", orgId || ""] });
    },
  });
}

export function useClockOut() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { employee_id: string; at?: string }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot clock in/out.");
      return api(apiPaths.workforceAttendanceClockOut, {
        method: "POST",
        body: JSON.stringify({ org_id: resolved, employee_id: payload.employee_id, at: payload.at ?? null }),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceDaily", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceCalendar", orgId || ""] });
    },
  });
}

export function useManualAttendanceEntry() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { employee_id: string; work_date: string; status: string; clock_in_at?: string | null; clock_out_at?: string | null; notes?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create attendance records.");
      return api(apiPaths.workforceAttendanceManual, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          employee_id: payload.employee_id,
          work_date: payload.work_date,
          status: payload.status,
          clock_in_at: payload.clock_in_at ?? null,
          clock_out_at: payload.clock_out_at ?? null,
          notes: payload.notes ?? null,
        }),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceDaily", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceCalendar", orgId || ""] });
    },
  });
}

export function useWorkforceCorrections(params: { status?: string; employee_id?: string; limit?: number }) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceCorrections(orgId || "", params),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      if (params.status) qs.set("status", params.status);
      if (params.employee_id) qs.set("employee_id", params.employee_id);
      if (params.limit) qs.set("limit", String(params.limit));
      const out = await api<WorkforceAttendanceCorrection[]>(`${apiPaths.workforceCorrections}?${qs.toString()}`);
      return out.map((row) => workforceAttendanceCorrectionSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useRequestCorrection() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { attendance_record_id: string; reason: string; proposed_status?: string | null; proposed_clock_in_at?: string | null; proposed_clock_out_at?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot request corrections.");
      const out = await api<WorkforceAttendanceCorrection>(apiPaths.workforceCorrections, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          attendance_record_id: payload.attendance_record_id,
          reason: payload.reason,
          proposed_status: payload.proposed_status ?? null,
          proposed_clock_in_at: payload.proposed_clock_in_at ?? null,
          proposed_clock_out_at: payload.proposed_clock_out_at ?? null,
        }),
      });
      return workforceAttendanceCorrectionSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceCorrections", orgId || ""] }),
  });
}

export function useReviewCorrection() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; status: "APPROVED" | "REJECTED"; reviewer_note?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot review corrections.");
      const out = await api<WorkforceAttendanceCorrection>(apiPaths.workforceCorrectionReview(payload.id), {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          status: payload.status,
          reviewer_note: payload.reviewer_note ?? null,
        }),
      });
      return workforceAttendanceCorrectionSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceCorrections", orgId || ""] }),
  });
}

export function useWorkforceLeaveTypes(includeInactive = true) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceLeaveTypes(orgId || "", includeInactive),
    queryFn: async () => {
      const out = await api<WorkforceLeaveType[]>(
        `${apiPaths.workforceLeaveTypes}?org_id=${orgId}&include_inactive=${includeInactive ? "true" : "false"}`,
      );
      return out.map((row) => workforceLeaveTypeSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforceLeaveType() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; code?: string | null; is_paid?: boolean; requires_approval?: boolean; is_active?: boolean }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create leave types.");
      const out = await api<WorkforceLeaveType>(apiPaths.workforceLeaveTypes, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name,
          code: payload.code ?? null,
          is_paid: payload.is_paid ?? true,
          requires_approval: payload.requires_approval ?? true,
          is_active: payload.is_active ?? true,
        }),
      });
      return workforceLeaveTypeSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceLeaveTypes", orgId || ""] }),
  });
}

export function useUpdateWorkforceLeaveType() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; name?: string | null; code?: string | null; is_paid?: boolean | null; requires_approval?: boolean | null; is_active?: boolean | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update leave types.");
      const out = await api<WorkforceLeaveType>(apiPaths.workforceLeaveTypeById(payload.id), {
        method: "PUT",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name ?? null,
          code: payload.code ?? null,
          is_paid: payload.is_paid ?? null,
          requires_approval: payload.requires_approval ?? null,
          is_active: payload.is_active ?? null,
        }),
      });
      return workforceLeaveTypeSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceLeaveTypes", orgId || ""] }),
  });
}

export function useDeactivateWorkforceLeaveType() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireOwner(orgId, role, "Only owners can deactivate leave types.");
      return api<{ ok: boolean }>(`${apiPaths.workforceLeaveTypeById(id)}?org_id=${resolved}`, { method: "DELETE" });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceLeaveTypes", orgId || ""] }),
  });
}

export function useWorkforceLeaveBalances(params: { employee_id?: string; year?: number; limit?: number }) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceLeaveBalances(orgId || "", params),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      if (params.employee_id) qs.set("employee_id", params.employee_id);
      if (params.year) qs.set("year", String(params.year));
      if (params.limit) qs.set("limit", String(params.limit));
      const out = await api<WorkforceLeaveBalance[]>(`${apiPaths.workforceLeaveBalances}?${qs.toString()}`);
      return out.map((row) => workforceLeaveBalanceSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useAllocateWorkforceLeaveBalance() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { employee_id: string; leave_type_id: string; year: number; allocated_days: string }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot allocate leave balances.");
      const out = await api<WorkforceLeaveBalance>(apiPaths.workforceLeaveBalanceAllocate, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          employee_id: payload.employee_id,
          leave_type_id: payload.leave_type_id,
          year: payload.year,
          allocated_days: payload.allocated_days,
        }),
      });
      return workforceLeaveBalanceSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workforceLeaveBalances", orgId || ""] }),
  });
}

export function useWorkforceLeaveRequests(params: { status?: string; employee_id?: string; from_date?: string; to_date?: string; limit?: number }) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceLeaveRequests(orgId || "", params),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      if (params.status) qs.set("status", params.status);
      if (params.employee_id) qs.set("employee_id", params.employee_id);
      if (params.from_date) qs.set("from_date", params.from_date);
      if (params.to_date) qs.set("to_date", params.to_date);
      if (params.limit) qs.set("limit", String(params.limit));
      const out = await api<WorkforceLeaveRequest[]>(`${apiPaths.workforceLeaveRequests}?${qs.toString()}`);
      return out.map((row) => workforceLeaveRequestSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforceLeaveRequest() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { employee_id: string; leave_type_id: string; start_date: string; end_date: string; days: string; reason?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot request leave.");
      const out = await api<WorkforceLeaveRequest>(apiPaths.workforceLeaveRequests, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          employee_id: payload.employee_id,
          leave_type_id: payload.leave_type_id,
          start_date: payload.start_date,
          end_date: payload.end_date,
          days: payload.days,
          reason: payload.reason ?? null,
        }),
      });
      return workforceLeaveRequestSchema.parse(out);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceLeaveRequests", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceLeaveBalances", orgId || ""] });
      // Auto-approved types write LEAVE rows; pending types do not — refetch is harmless.
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceDaily", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceCalendar", orgId || ""] });
    },
  });
}

export function useDecideWorkforceLeaveRequest() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; status: "APPROVED" | "REJECTED" | "CANCELLED"; reviewer_note?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot approve/reject leave.");
      const out = await api<WorkforceLeaveRequest>(apiPaths.workforceLeaveRequestDecision(payload.id), {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          status: payload.status,
          reviewer_note: payload.reviewer_note ?? null,
        }),
      });
      return workforceLeaveRequestSchema.parse(out);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceLeaveRequests", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceLeaveBalances", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceDaily", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAttendanceCalendar", orgId || ""] });
    },
  });
}

export function useWorkforceAnnouncements(includeArchived = false) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceAnnouncements(orgId || "", includeArchived),
    queryFn: async () => {
      const qs = new URLSearchParams({
        org_id: orgId || "",
        include_archived: includeArchived ? "true" : "false",
      });
      const out = await api<WorkforceAnnouncement[]>(`${apiPaths.workforceAnnouncements}?${qs.toString()}`);
      return out.map((row) => workforceAnnouncementSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useWorkforceAnnouncementDetail(announcementId: string | null) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforceAnnouncement(orgId || "", announcementId || ""),
    queryFn: async () => {
      const out = await api<WorkforceAnnouncement>(
        `${apiPaths.workforceAnnouncementById(announcementId!)}?org_id=${encodeURIComponent(orgId!)}`,
      );
      return workforceAnnouncementSchema.parse(out);
    },
    enabled: Boolean(orgId && announcementId),
  });
}

export function useWorkforceAnnouncementTemplates() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const canEdit = role === "OWNER" || role === "EDITOR";
  return useQuery({
    queryKey: qk.workforceAnnouncementTemplates(orgId || ""),
    queryFn: async () => {
      const resolved = requireEditor(orgId, role, "Only editors can manage announcement templates.");
      const out = await api<WorkforceAnnouncementTemplate[]>(
        `${apiPaths.workforceAnnouncementTemplates}?org_id=${encodeURIComponent(resolved)}`,
      );
      return out.map((row) => workforceAnnouncementTemplateSchema.parse(row));
    },
    enabled: Boolean(orgId && canEdit),
  });
}

export function useCreateWorkforceAnnouncementTemplate() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      body_template: string;
      code?: string | null;
      description?: string | null;
      automation_key?: string | null;
    }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create templates.");
      const out = await api<WorkforceAnnouncementTemplate>(apiPaths.workforceAnnouncementTemplates, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          name: payload.name,
          body_template: payload.body_template,
          code: payload.code ?? null,
          description: payload.description ?? null,
          automation_key: payload.automation_key ?? null,
        }),
      });
      return workforceAnnouncementTemplateSchema.parse(out);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["workforceAnnouncementTemplates", orgId || ""] }),
  });
}

export function useUpdateWorkforceAnnouncementTemplate() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      id: string;
      name?: string;
      body_template?: string;
      code?: string | null;
      code_clear?: boolean;
      description?: string | null;
      description_clear?: boolean;
      automation_key?: string | null;
      automation_clear?: boolean;
      is_active?: boolean;
    }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update templates.");
      const body: Record<string, unknown> = { org_id: resolved };
      if (payload.name !== undefined) body.name = payload.name;
      if (payload.body_template !== undefined) body.body_template = payload.body_template;
      if (payload.code_clear) body.code_clear = true;
      if (payload.code !== undefined) body.code = payload.code;
      if (payload.description_clear) body.description_clear = true;
      if (payload.description !== undefined) body.description = payload.description;
      if (payload.automation_clear) body.automation_clear = true;
      if (payload.automation_key !== undefined) body.automation_key = payload.automation_key;
      if (payload.is_active !== undefined) body.is_active = payload.is_active;
      const out = await api<WorkforceAnnouncementTemplate>(apiPaths.workforceAnnouncementTemplateById(payload.id), {
        method: "PUT",
        body: JSON.stringify(body),
      });
      return workforceAnnouncementTemplateSchema.parse(out);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["workforceAnnouncementTemplates", orgId || ""] }),
  });
}

export function useWorkforceAnnouncementAutomationKeys() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const canEdit = role === "OWNER" || role === "EDITOR";
  return useQuery({
    queryKey: ["workforceAnnouncementAutomationKeys", orgId || ""],
    queryFn: async () => {
      const resolved = requireEditor(orgId, role, "Only editors can view automation keys.");
      const out = await api<unknown>(
        `${apiPaths.workforceAnnouncementAutomationKeys}?org_id=${encodeURIComponent(resolved)}`,
      );
      return workforceAutomationKeysSchema.parse(out);
    },
    enabled: Boolean(orgId && canEdit),
  });
}

export async function uploadWorkforceAnnouncementAttachment(orgId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetchRaw(
    `${apiPaths.workforceAnnouncementAttachmentUpload}?org_id=${encodeURIComponent(orgId)}`,
    { method: "POST", body: form },
  );
  const json = await res.json();
  return workforceAnnouncementAttachmentUploadSchema.parse(json);
}

export function useWorkforceAnnouncementDeliveries(
  announcementId: string | null,
  options?: { enabled?: boolean; page?: number; pageSize?: number; status?: string | null },
) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const canEdit = role === "OWNER" || role === "EDITOR";
  const page = options?.page ?? 1;
  const pageSize = options?.pageSize ?? 50;
  const status = options?.status ?? "ALL";
  return useQuery({
    queryKey: qk.workforceAnnouncementDeliveries(orgId || "", announcementId || "", page, pageSize, status),
    queryFn: async () => {
      const resolved = requireEditor(orgId, role, "Only editors can view delivery logs.");
      const qs = new URLSearchParams({
        org_id: resolved,
        page: String(page),
        page_size: String(pageSize),
      });
      if (status && status !== "ALL") qs.set("status", status);
      const out = await api<unknown>(`${apiPaths.workforceAnnouncementDeliveries(announcementId!)}?${qs.toString()}`);
      return workforceAnnouncementDeliveryListSchema.parse(out) as WorkforceAnnouncementDeliveryList;
    },
    enabled: Boolean(orgId && announcementId && canEdit && (options?.enabled ?? true)),
  });
}

export function useCreateWorkforceAnnouncement() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      title: string;
      body: string;
      priority?: string;
      pinned?: boolean;
      acknowledgement_required?: boolean;
      expires_at?: string | null;
      scheduled_publish_at?: string | null;
      audience_kind?: string;
      audience_ids?: string[];
      attachments?: { name: string; url: string }[];
      send_email_on_publish?: boolean;
      template_id?: string | null;
    }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create announcements.");
      const out = await api<WorkforceAnnouncement>(apiPaths.workforceAnnouncements, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          title: payload.title,
          body: payload.body,
          priority: payload.priority ?? "NORMAL",
          pinned: payload.pinned ?? false,
          acknowledgement_required: payload.acknowledgement_required ?? false,
          expires_at: payload.expires_at ?? null,
          scheduled_publish_at: payload.scheduled_publish_at ?? null,
          audience_kind: payload.audience_kind ?? "ORG_ALL",
          audience_ids: payload.audience_ids?.length ? payload.audience_ids : null,
          attachments: payload.attachments?.length ? payload.attachments : null,
          send_email_on_publish: payload.send_email_on_publish ?? false,
          template_id: payload.template_id ?? null,
        }),
      });
      return workforceAnnouncementSchema.parse(out);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["workforceAnnouncements", orgId || ""] }),
  });
}

export function useUpdateWorkforceAnnouncement() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (p: {
      id: string;
      title?: string;
      body?: string;
      priority?: string;
      pinned?: boolean;
      acknowledgement_required?: boolean;
      expires_at?: string | null;
      clear_expires_at?: boolean;
      scheduled_publish_at?: string | null;
      clear_scheduled_publish_at?: boolean;
      audience_kind?: string;
      audience_ids?: string[] | null;
      audience_ids_clear?: boolean;
      attachments?: { name: string; url: string }[] | null;
      clear_attachments?: boolean;
      send_email_on_publish?: boolean;
      template_id?: string | null;
      clear_template_id?: boolean;
    }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot update announcements.");
      const body: Record<string, unknown> = { org_id: resolved };
      if (p.title !== undefined) body.title = p.title;
      if (p.body !== undefined) body.body = p.body;
      if (p.priority !== undefined) body.priority = p.priority;
      if (p.pinned !== undefined) body.pinned = p.pinned;
      if (p.acknowledgement_required !== undefined) body.acknowledgement_required = p.acknowledgement_required;
      if (p.clear_expires_at) body.expires_at = null;
      else if (p.expires_at !== undefined) body.expires_at = p.expires_at;
      if (p.clear_scheduled_publish_at) body.scheduled_publish_at = null;
      else if (p.scheduled_publish_at !== undefined) body.scheduled_publish_at = p.scheduled_publish_at;
      if (p.audience_kind !== undefined) body.audience_kind = p.audience_kind;
      if (p.audience_ids_clear) body.audience_ids_clear = true;
      if (p.audience_ids !== undefined) body.audience_ids = p.audience_ids;
      if (p.clear_attachments) body.attachments_clear = true;
      if (p.attachments !== undefined) body.attachments = p.attachments;
      if (p.send_email_on_publish !== undefined) body.send_email_on_publish = p.send_email_on_publish;
      if (p.clear_template_id) body.template_clear = true;
      if (p.template_id !== undefined) body.template_id = p.template_id;
      const out = await api<WorkforceAnnouncement>(apiPaths.workforceAnnouncementById(p.id), {
        method: "PUT",
        body: JSON.stringify(body),
      });
      return workforceAnnouncementSchema.parse(out);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncements", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncement", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncementDeliveries", orgId || ""] });
    },
  });
}

export function usePublishWorkforceAnnouncement() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot publish announcements.");
      const out = await api<WorkforceAnnouncement>(apiPaths.workforceAnnouncementPublish(id), {
        method: "POST",
        body: JSON.stringify({ org_id: resolved }),
      });
      return workforceAnnouncementSchema.parse(out);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncements", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncement", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncementDeliveries", orgId || ""] });
    },
  });
}

export function useArchiveWorkforceAnnouncement() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot archive announcements.");
      const out = await api<WorkforceAnnouncement>(apiPaths.workforceAnnouncementArchive(id), {
        method: "POST",
        body: JSON.stringify({ org_id: resolved }),
      });
      return workforceAnnouncementSchema.parse(out);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncements", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncement", orgId || ""] });
    },
  });
}

export function useAcknowledgeWorkforceAnnouncement() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const resolved = requireOrgId(orgId);
      const out = await api<unknown>(apiPaths.workforceAnnouncementAcknowledge(id), {
        method: "POST",
        body: JSON.stringify({ org_id: resolved }),
      });
      return workforceAnnouncementReceiptSchema.parse(out);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncements", orgId || ""] });
      void qc.invalidateQueries({ queryKey: ["workforceAnnouncement", orgId || ""] });
    },
  });
}

export function useWorkforcePayrollPeriods() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforcePayrollPeriods(orgId || ""),
    queryFn: async () => {
      const out = await api<WorkforcePayrollPeriod[]>(`${apiPaths.workforcePayrollPeriods}?org_id=${orgId}&limit=100`);
      return out.map((row) => workforcePayrollPeriodSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateWorkforcePayrollPeriod() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { start_date: string; end_date: string }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot create payroll periods.");
      const out = await api<WorkforcePayrollPeriod>(apiPaths.workforcePayrollPeriods, {
        method: "POST",
        body: JSON.stringify({ org_id: resolved, start_date: payload.start_date, end_date: payload.end_date }),
      });
      return workforcePayrollPeriodSchema.parse(out);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.workforcePayrollPeriods(orgId || "") }),
  });
}

export function useGenerateWorkforcePayrollDraft() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { payroll_period_id: string; overtime_multiplier?: string; include_inactive_employees?: boolean }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot generate payroll.");
      const out = await api<WorkforcePayrollEntry[]>(apiPaths.workforcePayrollGenerate(payload.payroll_period_id), {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          payroll_period_id: payload.payroll_period_id,
          overtime_multiplier: payload.overtime_multiplier ?? "1.5",
          include_inactive_employees: payload.include_inactive_employees ?? false,
        }),
      });
      return out.map((row) => workforcePayrollEntrySchema.parse(row));
    },
    onSuccess: async (_data, vars) => {
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollEntries(orgId || "", vars.payroll_period_id) });
    },
  });
}

export function useWorkforcePayrollEntries(periodId: string) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforcePayrollEntries(orgId || "", periodId),
    queryFn: async () => {
      const out = await api<WorkforcePayrollEntry[]>(`${apiPaths.workforcePayrollEntries(periodId)}?org_id=${orgId}`);
      return out.map((row) => workforcePayrollEntrySchema.parse(row));
    },
    enabled: Boolean(orgId && periodId),
  });
}

export function useApproveWorkforcePayrollPeriod() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (periodId: string) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot approve payroll.");
      const out = await api<WorkforcePayrollPeriod>(apiPaths.workforcePayrollApprove(periodId), {
        method: "POST",
        body: JSON.stringify({ org_id: resolved }),
      });
      return workforcePayrollPeriodSchema.parse(out);
    },
    onSuccess: async (_data, periodId) => {
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollPeriods(orgId || "") });
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollEntries(orgId || "", periodId) });
    },
  });
}

export function useMarkPaidWorkforcePayrollPeriod() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (periodId: string) => {
      const resolved = requireOwner(orgId, role, "Only owners can mark payroll paid.");
      const out = await api<WorkforcePayrollPeriod>(apiPaths.workforcePayrollMarkPaid(periodId), {
        method: "POST",
        body: JSON.stringify({ org_id: resolved }),
      });
      return workforcePayrollPeriodSchema.parse(out);
    },
    onSuccess: async (_data, periodId) => {
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollPeriods(orgId || "") });
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollEntries(orgId || "", periodId) });
    },
  });
}

export function useCreateWorkforcePayrollAdjustment() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { payroll_period_id: string; payroll_entry_id: string; employee_id: string; kind: string; amount: string; label?: string | null; notes?: string | null }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot add adjustments.");
      const out = await api<WorkforcePayrollAdjustment>(apiPaths.workforcePayrollAdjustments, {
        method: "POST",
        body: JSON.stringify({
          org_id: resolved,
          payroll_period_id: payload.payroll_period_id,
          payroll_entry_id: payload.payroll_entry_id,
          employee_id: payload.employee_id,
          kind: payload.kind,
          amount: payload.amount,
          label: payload.label ?? null,
          notes: payload.notes ?? null,
        }),
      });
      return workforcePayrollAdjustmentSchema.parse(out);
    },
    onSuccess: async (_data, vars) => {
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollEntries(orgId || "", vars.payroll_period_id) });
      await qc.invalidateQueries({ queryKey: qk.workforcePayslipPreview(orgId || "", vars.payroll_entry_id) });
    },
  });
}

export function useDeleteWorkforcePayrollAdjustment() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { adjustment_id: string; payroll_period_id: string; payroll_entry_id: string }) => {
      const resolved = requireEditor(orgId, role, "Viewer role cannot delete adjustments.");
      return api<{ ok: boolean }>(
        `${apiPaths.workforcePayrollAdjustmentById(payload.adjustment_id)}?org_id=${resolved}&payroll_period_id=${payload.payroll_period_id}`,
        { method: "DELETE" },
      );
    },
    onSuccess: async (_data, vars) => {
      await qc.invalidateQueries({ queryKey: qk.workforcePayrollEntries(orgId || "", vars.payroll_period_id) });
      await qc.invalidateQueries({ queryKey: qk.workforcePayslipPreview(orgId || "", vars.payroll_entry_id) });
    },
  });
}

export function useWorkforcePayslipPreview(entryId: string) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.workforcePayslipPreview(orgId || "", entryId),
    queryFn: async () => {
      const out = await api<WorkforcePayslipPreview>(`${apiPaths.workforcePayrollPayslip(entryId)}?org_id=${orgId}`, {
        schema: workforcePayslipPreviewSchema,
      });
      return workforcePayslipPreviewSchema.parse(out);
    },
    enabled: Boolean(orgId && entryId),
  });
}

