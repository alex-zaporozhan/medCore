import { Outlet, useLocation, Navigate } from "react-router-dom";
import { getAdminToken } from "@/api/client";

export default function AdminAuthGuard() {
  const location = useLocation();
  const isLoginPage = location.pathname === "/admin/login";
  const token = getAdminToken();

  if (isLoginPage) {
    if (token) {
      return <Navigate to="/admin" replace />;
    }
    return <Outlet />;
  }

  if (!token) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
