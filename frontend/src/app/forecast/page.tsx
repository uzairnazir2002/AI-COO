import ProtectedLayout from "@/app/app/layout";
import ForecastPage from "@/app/app/forecast/page";

export default function ForecastRoutePage() {
  return (
    <ProtectedLayout>
      <ForecastPage />
    </ProtectedLayout>
  );
}
