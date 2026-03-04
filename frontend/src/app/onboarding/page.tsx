import { redirect } from "next/navigation";

export default function LegacyOnboardingRedirect() {
  redirect("/app/orgs");
}
