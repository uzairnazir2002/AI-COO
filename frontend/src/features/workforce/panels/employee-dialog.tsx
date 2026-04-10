"use client";

import { useMemo, useState } from "react";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Location, WorkforceDepartment, WorkforceEmployee, WorkforceTitle } from "@/types/domain";

type SubmitPayload = Partial<WorkforceEmployee> & { first_name: string; last_name: string };

export function EmployeeDialog({
  open,
  onOpenChange,
  title,
  submitLabel,
  pending,
  initial,
  departments,
  titles,
  locations,
  managerOptions,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (value: boolean) => void;
  title: string;
  submitLabel: string;
  pending: boolean;
  initial?: WorkforceEmployee;
  departments: WorkforceDepartment[];
  titles: WorkforceTitle[];
  locations: Location[];
  managerOptions: WorkforceEmployee[];
  onSubmit: (payload: SubmitPayload) => Promise<void>;
}) {
  const deptOptions = useMemo(() => departments.slice().sort((a, b) => a.name.localeCompare(b.name)), [departments]);
  const titleOptions = useMemo(() => titles.slice().sort((a, b) => a.name.localeCompare(b.name)), [titles]);
  const locationOptions = useMemo(() => locations.slice().sort((a, b) => a.name.localeCompare(b.name)), [locations]);
  const mgrOptions = useMemo(
    () => managerOptions.slice().sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`)),
    [managerOptions],
  );

  const [employeeCode, setEmployeeCode] = useState(initial?.employee_code ?? "");
  const [firstName, setFirstName] = useState(initial?.first_name ?? "");
  const [lastName, setLastName] = useState(initial?.last_name ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  const [departmentId, setDepartmentId] = useState<string>(initial?.department_id ?? "__none__");
  const [titleId, setTitleId] = useState<string>(initial?.title_id ?? "__none__");
  const [managerId, setManagerId] = useState<string>(initial?.manager_employee_id ?? "__none__");
  const [locationId, setLocationId] = useState<string>(initial?.location_id ?? "__none__");
  const [employmentType, setEmploymentType] = useState<string>(initial?.employment_type ?? "FULL_TIME");
  const [employmentStatus, setEmploymentStatus] = useState<string>(initial?.employment_status ?? "ACTIVE");
  const [salaryType, setSalaryType] = useState<string>(initial?.salary_type ?? "SALARIED");
  const [baseSalary, setBaseSalary] = useState<string>(initial?.base_salary ?? "");
  const [hourlyRate, setHourlyRate] = useState<string>(initial?.hourly_rate ?? "");

  function resetFromInitial() {
    setEmployeeCode(initial?.employee_code ?? "");
    setFirstName(initial?.first_name ?? "");
    setLastName(initial?.last_name ?? "");
    setEmail(initial?.email ?? "");
    setPhone(initial?.phone ?? "");
    setDepartmentId(initial?.department_id ?? "__none__");
    setTitleId(initial?.title_id ?? "__none__");
    setManagerId(initial?.manager_employee_id ?? "__none__");
    setLocationId(initial?.location_id ?? "__none__");
    setEmploymentType(initial?.employment_type ?? "FULL_TIME");
    setEmploymentStatus(initial?.employment_status ?? "ACTIVE");
    setSalaryType(initial?.salary_type ?? "SALARIED");
    setBaseSalary(initial?.base_salary ?? "");
    setHourlyRate(initial?.hourly_rate ?? "");
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) resetFromInitial();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>Keep it minimal now; you can enrich HR records in later workflows.</DialogDescription>
        </DialogHeader>

        <form
          className="grid gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            await onSubmit({
              employee_code: employeeCode.trim() || null,
              first_name: firstName.trim(),
              last_name: lastName.trim(),
              email: email.trim() || null,
              phone: phone.trim() || null,
              department_id: departmentId === "__none__" ? null : departmentId,
              title_id: titleId === "__none__" ? null : titleId,
              manager_employee_id: managerId === "__none__" ? null : managerId,
              location_id: locationId === "__none__" ? null : locationId,
              employment_type: employmentType,
              employment_status: employmentStatus,
              salary_type: salaryType,
              base_salary: salaryType === "SALARIED" ? (baseSalary.trim() || null) : null,
              hourly_rate: salaryType === "HOURLY" ? (hourlyRate.trim() || null) : null,
            });
          }}
        >
          <div className="grid gap-3 md:grid-cols-3">
            <Input placeholder="Employee code (optional)" value={employeeCode} onChange={(e) => setEmployeeCode(e.target.value)} />
            <Input placeholder="First name" value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
            <Input placeholder="Last name" value={lastName} onChange={(e) => setLastName(e.target.value)} required />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <Input placeholder="Email (optional)" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Input placeholder="Phone (optional)" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Select value={departmentId} onValueChange={setDepartmentId}>
              <SelectTrigger><SelectValue placeholder="Department" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">No department</SelectItem>
                {deptOptions.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.name}{d.is_active ? "" : " (inactive)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={titleId} onValueChange={setTitleId}>
              <SelectTrigger><SelectValue placeholder="Title" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">No title</SelectItem>
                {titleOptions.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}{t.is_active ? "" : " (inactive)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={managerId} onValueChange={setManagerId}>
              <SelectTrigger><SelectValue placeholder="Manager" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">No manager</SelectItem>
                {mgrOptions.map((e) => (
                  <SelectItem key={e.id} value={e.id}>
                    {e.first_name} {e.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={locationId} onValueChange={setLocationId}>
              <SelectTrigger><SelectValue placeholder="Location" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">All locations</SelectItem>
                {locationOptions.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.name}{l.is_active ? "" : " (inactive)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Select value={employmentStatus} onValueChange={setEmploymentStatus}>
              <SelectTrigger><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ACTIVE">Active</SelectItem>
                <SelectItem value="ON_LEAVE">On leave</SelectItem>
                <SelectItem value="OFFBOARDED">Offboarded</SelectItem>
                <SelectItem value="TERMINATED">Terminated</SelectItem>
              </SelectContent>
            </Select>
            <Select value={employmentType} onValueChange={setEmploymentType}>
              <SelectTrigger><SelectValue placeholder="Employment type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="FULL_TIME">Full-time</SelectItem>
                <SelectItem value="PART_TIME">Part-time</SelectItem>
                <SelectItem value="CONTRACTOR">Contractor</SelectItem>
                <SelectItem value="INTERN">Intern</SelectItem>
              </SelectContent>
            </Select>
            <Select value={salaryType} onValueChange={setSalaryType}>
              <SelectTrigger><SelectValue placeholder="Salary type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="SALARIED">Salaried</SelectItem>
                <SelectItem value="HOURLY">Hourly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="Base salary (e.g. 80000.00)"
              value={baseSalary}
              onChange={(e) => setBaseSalary(e.target.value)}
              disabled={salaryType !== "SALARIED"}
            />
            <Input
              placeholder="Hourly rate (e.g. 22.50)"
              value={hourlyRate}
              onChange={(e) => setHourlyRate(e.target.value)}
              disabled={salaryType !== "HOURLY"}
            />
          </div>

          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending || firstName.trim().length === 0 || lastName.trim().length === 0}>
              {submitLabel}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

