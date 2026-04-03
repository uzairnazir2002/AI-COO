import ProtectedLayout from "@/app/app/layout";
import AdminConsoleRoutePage from "@/app/app/admin-console/page";

export default function AdminConsolePageAlias() {
  return (
    <ProtectedLayout>
      <AdminConsoleRoutePage />
    </ProtectedLayout>
  );
}

