import ProtectedLayout from "@/app/app/layout";
import ActivityPage from "@/app/app/activity/page";

export default function ActivityRoutePage() {
  return (
    <ProtectedLayout>
      <ActivityPage />
    </ProtectedLayout>
  );
}
