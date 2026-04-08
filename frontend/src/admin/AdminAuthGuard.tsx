import { Outlet, useLocation, Navigate, createSearchParams } from "react-router-dom";
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
    const returnTo = `${location.pathname}${location.search}`;
    const search = `?${createSearchParams({ returnTo }).toString()}`;
    return (
      <Navigate
        to={{ pathname: ROUTE_PATHS.admin.login, search }}
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <Outlet />;
}
