import ProtectedLayout from "@/app/app/layout";
import SettingsPage from "@/app/app/settings/page";

export default function SettingsRoutePage() {
  return (
    <ProtectedLayout>
      <SettingsPage />
    </ProtectedLayout>
  );
}
