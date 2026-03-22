import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useClinics, usePatientConversation } from "@/hooks";
import { Anchor, AppShell, Badge, Box, Button, Group, Text, Alert, MantineProvider } from "@mantine/core";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { ROUTE_PATHS } from "@/routePaths";
import { isPatientLoginPath } from "@/routePathUtils";
import { appTheme } from "@/theme";

const SELECTED_CLINIC_KEY = "app.selectedClinicId";

const mainNav = [
  { to: ROUTE_PATHS.patient.home, label: "Главная" },
  { to: ROUTE_PATHS.patient.booking, label: "Запись" },
  { to: ROUTE_PATHS.patient.chat, label: "Чат" },
  { to: ROUTE_PATHS.patient.profile, label: "Профиль" },
];
const mainNavWithHistory = [
  ...mainNav,
  { to: ROUTE_PATHS.patient.history, label: "История" },
];

/** Спокойный светлый chrome: без сплошной «плашки» primary — только тонкая линия бренда клиники и тень. */
const patientChromeHeader = {
  backgroundColor: "var(--mantine-color-white)",
  borderBottom: "1px solid var(--divider)",
  boxShadow: "var(--mantine-shadow-xs)",
} as const;

const patientChromeBottom = {
  backgroundColor: "var(--mantine-color-white)",
  boxShadow: "0 -1px 2px rgba(15, 23, 42, 0.06)",
} as const;

export default function AppLayout() {
  const { accessToken, logout, patientId } = usePatientAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { data: clinics } = useClinics();
  const { data: conversation } = usePatientConversation(patientId ?? null, accessToken);
  const chatUnread = conversation?.unread_by_patient_count ?? 0;
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );

  const selectedClinicId =
    typeof localStorage !== "undefined" ? localStorage.getItem(SELECTED_CLINIC_KEY) : null;
  const themeClinic = clinics?.find((c) => c.id === selectedClinicId);

  useEffect(() => {
    document.body.classList.add("app-pwa-body");
    return () => {
      document.body.classList.remove("app-pwa-body");
    };
  }, []);

  useEffect(() => {
    if (!themeClinic?.theme_font_family) return;
    const root = document.documentElement;
    root.style.setProperty("--font-family-app", themeClinic.theme_font_family);
    return () => {
      root.style.removeProperty("--font-family-app");
    };
  }, [themeClinic?.id, themeClinic?.theme_font_family]);

  useEffect(() => {
    const onLoginPage = isPatientLoginPath(location.pathname);
    if (!accessToken && !onLoginPage) {
      navigate(ROUTE_PATHS.other.login, { replace: true });
    }
  }, [accessToken, navigate, location.pathname]);

  useEffect(() => {
    function handleOnline() {
      setIsOnline(true);
    }

    function handleOffline() {
      setIsOnline(false);
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const brandAccent = themeClinic?.theme_primary_color ?? undefined;

  return (
    <MantineProvider theme={appTheme} forceColorScheme="light">
    <AppShell header={{ height: 56 }} padding="md" className="app-patient-root">
      <AppShell.Header
        style={{
          ...patientChromeHeader,
          ...(brandAccent ? { borderTop: `3px solid ${brandAccent}` } : {}),
        }}
      >
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          {themeClinic?.theme_logo_url ? (
            <img
              src={themeClinic.theme_logo_url}
              alt=""
              style={{ height: 32, maxWidth: 120, objectFit: "contain" }}
            />
          ) : (
            <Text fw={700} c="gray.9" visibleFrom="xs">
              Dental Booking
            </Text>
          )}
          <Group gap="md" style={{ flex: 1, justifyContent: "center" }} visibleFrom="sm">
            {mainNavWithHistory.map((item) => {
              const isChat = item.to === ROUTE_PATHS.patient.chat;
              const showBadge = isChat && chatUnread > 0;
              const active = location.pathname === item.to;
              return (
                <Anchor
                  key={item.to}
                  component={Link}
                  to={item.to}
                  size="sm"
                  fw={active ? 600 : 500}
                  c={active ? "dark.9" : "gray.6"}
                  style={{ display: "flex", alignItems: "center", gap: 4 }}
                >
                  {item.label}
                  {showBadge && (
                    <Badge size="xs" variant="dot" color="red">
                      {chatUnread > 99 ? "99+" : chatUnread}
                    </Badge>
                  )}
                </Anchor>
              );
            })}
          </Group>
          <Group gap="xs">
            {accessToken && (
              <Button variant="subtle" size="compact-sm" color="gray" onClick={() => {
                  logout();
                  navigate(ROUTE_PATHS.marketing.landing);
                }}
              >
                Выйти
              </Button>
            )}
            <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="xs" c="dimmed">
              На главную
            </Anchor>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Main
        className="app-main-with-bottom-nav app-patient-main"
        style={{ backgroundColor: "var(--bg-main)", minHeight: "100%" }}
      >
        {!isOnline && (
          <Alert
            color="yellow"
            variant="light"
            style={{ borderRadius: 0, borderBottom: "1px solid var(--divider)" }}
          >
            Нет подключения к интернету. Данные о записях могут быть неактуальны, создание новых
            записей недоступно до восстановления связи.
          </Alert>
        )}
        <Outlet />
      </AppShell.Main>

      <Box
        hiddenFrom="sm"
        className="app-bottom-nav app-patient-bottom-nav"
        component="nav"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          height: 56,
          ...patientChromeBottom,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-around",
          zIndex: 100,
        }}
      >
        {mainNav.map((item) => {
          const isActive = location.pathname === item.to;
          const isChat = item.to === ROUTE_PATHS.patient.chat;
          const showBadge = isChat && chatUnread > 0;
          return (
            <Anchor
              key={item.to}
              component={Link}
              to={item.to}
              size="sm"
              fw={isActive ? 600 : 500}
              c={isActive ? "dark.9" : "gray.6"}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 2,
                textDecoration: "none",
                padding: "6px 12px",
              }}
            >
              {item.label}
              {showBadge && (
                <Badge size="xs" variant="dot" color="red">
                  {chatUnread > 99 ? "99+" : chatUnread}
                </Badge>
              )}
            </Anchor>
          );
        })}
      </Box>
    </AppShell>
    </MantineProvider>
  );
}
