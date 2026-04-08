import { ROUTE_PATHS } from "@/routePaths";
import { Navigate } from "react-router-dom";

/** Legacy `/login` → главная с подсказкой про вход по ссылке клиники. */
export default function LoginPage() {
  return <Navigate to={`${ROUTE_PATHS.marketing.landing}?patientEntry=need-clinic`} replace />;
}
