import ProtectedLayout from "@/app/app/layout";
import BudgetsPage from "@/app/app/budgets/page";

export default function BudgetsRoutePage() {
  return (
    <ProtectedLayout>
      <BudgetsPage />
    </ProtectedLayout>
  );
}
