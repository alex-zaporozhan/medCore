import { ROUTE_PATHS, patientPublicLoginSearch } from "@/routePaths";
import { Navigate } from "react-router-dom";

/** Legacy обёртка: тот же публичный вход, что и маршрут `/login` в `App.tsx`. */
export default function LoginPage() {
  return <Navigate to={`${ROUTE_PATHS.other.login}${patientPublicLoginSearch("need-clinic")}`} replace />;
}
