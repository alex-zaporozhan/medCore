import { PlatformFounderSessionProvider } from "@/marketing/contexts/PlatformFounderSessionContext";
import { clearFounderToken, getFounderToken, setFounderToken as persistFounderToken } from "@/marketing/platformFounderSession";
import { ROUTE_PATHS } from "@/routePaths";
import { Box, Button, Group, Text } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, Outlet, useLocation, useNavigate, createSearchParams } from "react-router-dom";

/**
 * Оболочка кабинета Основателя (FE-E2): навигация между дашбордом и операционными экранами.
 */
export default function PlatformFounderLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setTokenState] = useState(() => getFounderToken()?.trim() ?? "");

  useEffect(() => {
    const t = getFounderToken()?.trim() ?? "";
    setTokenState(t);
  }, [location.pathname]);

  const setToken = useCallback((t: string) => {
    const v = t.trim();
    persistFounderToken(v);
    setTokenState(v);
  }, []);

  const logout = useCallback(() => {
    clearFounderToken();
    setTokenState("");
    navigate({ pathname: ROUTE_PATHS.platform.login }, { replace: true });
  }, [navigate]);

  const session = useMemo(
    () => ({
      token,
      setToken,
      logout,
    }),
    [token, setToken, logout],
  );

  if (!token) {
    const returnTo = `${location.pathname}${location.search}`;
    const search = returnTo ? `?${createSearchParams({ returnTo }).toString()}` : "";
    return (
      <Navigate to={{ pathname: ROUTE_PATHS.platform.login, search }} replace state={{ from: location.pathname }} />
    );
  }

  const navBtn = (path: string, label: string) => (
    <Button
      key={path}
      component={Link}
      to={path}
      variant={location.pathname === path ? "light" : "subtle"}
      size="xs"
    >
      {label}
    </Button>
  );

  return (
    <PlatformFounderSessionProvider value={session}>
      <Box style={{ minHeight: "100vh", background: "var(--bg-main)" }}>
        <Box
          px="md"
          py="sm"
          style={{
            borderBottom: "1px solid var(--divider)",
            background: "var(--bg-card)",
          }}
        >
          <Group justify="space-between" wrap="wrap">
            <Group gap="xs">
              <Text size="sm" fw={600}>
                Основатель платформы
              </Text>
              {navBtn(ROUTE_PATHS.platform.dashboard, "Обзор")}
              {navBtn(ROUTE_PATHS.platform.provisionQueue, "Очередь внедрения")}
              {navBtn(ROUTE_PATHS.platform.leads, "Заявки")}
            </Group>
            <Button variant="default" size="xs" onClick={logout}>
              Выйти
            </Button>
          </Group>
        </Box>
        <Outlet />
      </Box>
    </PlatformFounderSessionProvider>
  );
}
