import { redirect } from "next/navigation";

export default function LegacyTransactionsRedirect() {
  redirect("/app/transactions");
}
