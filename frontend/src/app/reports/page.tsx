import ProtectedLayout from "@/app/app/layout";
import ReportsPage from "@/app/app/reports/page";

export default async function ReportsRoutePage() {
  return (
    <ProtectedLayout>
      <ReportsPage />
    </ProtectedLayout>
  );
}
