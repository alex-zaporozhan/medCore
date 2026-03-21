import { Outlet, useLocation, Navigate } from "react-router-dom";
import { getAdminToken } from "@/api/client";
import { ROUTE_PATHS } from "@/routePaths";
import { isAdminLoginPath } from "@/routePathUtils";

export default function AdminAuthGuard() {
  const location = useLocation();
  const isLoginPage = isAdminLoginPath(location.pathname);
  const token = getAdminToken();

  if (isLoginPage) {
    if (token) {
      return <Navigate to={ROUTE_PATHS.admin.dashboard} replace />;
    }
    return <Outlet />;
  }

  if (!token) {
    return (
      <Navigate to={ROUTE_PATHS.admin.login} replace state={{ from: location.pathname }} />
    );
  }

  return <Outlet />;
}
