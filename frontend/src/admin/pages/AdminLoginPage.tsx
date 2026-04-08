import { ROUTE_PATHS } from "@/routePaths";
import { Navigate } from "react-router-dom";

/** Паритет: `/admin/login` — канонический путь (см. `ClinicSignInPage` в `App.tsx`). */
export default function AdminLoginPage() {
  return <Navigate to={ROUTE_PATHS.admin.login} replace />;
}
