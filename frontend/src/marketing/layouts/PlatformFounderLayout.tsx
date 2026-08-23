import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";
import { PlatformFounderSessionProvider } from "@/marketing/contexts/PlatformFounderSessionContext";
import { clearFounderToken, getFounderToken, setFounderToken as persistFounderToken } from "@/marketing/platformFounderSession";
import { ROUTE_PATHS } from "@/routePaths";
import { Box, Button, Group, Text } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, Outlet, useLocation, useNavigate, createSearchParams } from "react-router-dom";

/** Founder cabinet shell: dashboard vs operational screens. */
export default function PlatformFounderLayout() {
  const { t } = useTranslation("auth");
  const { t: tc } = useTranslation("common");
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
                {t("founder.pageTitle")}
              </Text>
              {navBtn(ROUTE_PATHS.platform.dashboard, t("founder.navOverview"))}
              {navBtn(ROUTE_PATHS.platform.provisionQueue, t("founder.navProvision"))}
              {navBtn(ROUTE_PATHS.platform.leads, t("founder.navLeads"))}
            </Group>
            <Group gap="xs" wrap="nowrap">
              <UiLocaleSwitch />
              <Button variant="default" size="xs" onClick={logout}>
                {tc("logout")}
              </Button>
            </Group>
          </Group>
        </Box>
        <Outlet />
      </Box>
    </PlatformFounderSessionProvider>
  );
}
