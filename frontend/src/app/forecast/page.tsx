import { redirect } from "next/navigation";

export default function LegacyForecastRedirect() {
  redirect("/app/forecast");
}
