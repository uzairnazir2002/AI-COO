import ProtectedLayout from "@/app/app/layout";
import TransactionsPage from "@/app/app/transactions/page";

export default function TransactionsRoutePage() {
  return (
    <ProtectedLayout>
      <TransactionsPage />
    </ProtectedLayout>
  );
}
