import ProtectedLayout from "@/app/app/layout";
import DashboardPage from "@/app/app/dashboard/page";

export default async function DashboardRoutePage() {
  return (
    <ProtectedLayout>
      <DashboardPage />
    </ProtectedLayout>
  );
}
