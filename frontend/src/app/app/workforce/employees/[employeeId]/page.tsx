import { EmployeeDetailClient } from "@/features/workforce/containers/employee-detail-client";

export default async function WorkforceEmployeeDetailPage({
  params,
}: {
  params: Promise<{ employeeId: string }>;
}) {
  const resolved = await params;
  return <EmployeeDetailClient employeeId={resolved.employeeId} />;
}

