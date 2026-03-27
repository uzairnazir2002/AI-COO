import ProtectedLayout from "@/app/app/layout";
import OnboardingPage from "@/app/app/onboarding/page";

export default function OnboardingRoutePage() {
  return (
    <ProtectedLayout>
      <OnboardingPage />
    </ProtectedLayout>
  );
}
