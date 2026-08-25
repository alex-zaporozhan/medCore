import {
  ActionIcon,
  Alert,
  Anchor,
  AppShell,
  Badge,
  Box,
  Button,
  Container,
  Group,
  Modal,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Text,
  Textarea,
  UnstyledButton,
} from "@mantine/core";
import { Spotlight, spotlight } from "@mantine/spotlight";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { useMemo, useState, useCallback, useEffect } from "react";
import { useMediaQuery } from "@mantine/hooks";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { clearAdminToken } from "@/api/client";
import { useAdminOmniChats } from "@/hooks/useAdminOmniChat";
import {
  IconSearch,
  IconMenu2,
  IconDashboard,
  IconCalendar,
  IconMessageCircle,
  IconBriefcase,
  IconCash,
  IconGift,
  IconListCheck,
  IconChartBar,
  IconSettings,
  IconChevronLeft,
  IconChevronRight,
  IconStethoscope,
  IconCalendarWeek,
  IconUserCircle,
  IconClipboardList,
  IconBuilding,
  IconReceipt,
  IconListSearch,
  IconRefresh,
  IconBrandWhatsapp,
  IconShield,
  IconBook,
  IconHome2,
  IconDoorExit,
  IconRobot,
  IconUser,
  IconCalendarEvent,
  IconTarget,
  IconCode,
  IconShoppingCart,
  IconDatabase,
  IconDownload,
  IconCoin,
} from "@tabler/icons-react";
import type { SpotlightActionData } from "@mantine/spotlight";
import { useAdminSearch } from "@/hooks/useAdminSearch";
import { useAiAgent } from "@/hooks/useAiAgent";
import { useAiFeatures, getAiFeatureBadgeColor, getAiFeatureStatusText, getAiFeatureTooltip } from "@/shared/aiFeatures";
import { logUiEvent } from "@/shared/uiEvents";
import { ROUTE_PATHS } from "@/routePaths";
import type enNav from "@/i18n/locales/en/nav.json";
import { ADMIN_PERM_PATIENTS_PII_READ, ADMIN_PERM_RBAC_MANAGE } from "@/shared/adminPermissions";
import { SEMANTIC } from "@/shared/semanticUi";
import { useAdminSession } from "@/hooks/useAdminSession";
import { BOX_HIDDEN_ADMIN_PATHS, isBoxEdition } from "@/config/edition";
import { ADMIN_NAV_PATH_ENTITLEMENT_KEY } from "@/shared/adminEntitlementNav";
import { PersonCardModalHost, PersonCardProvider } from "@/shared/ui";
import { ADMIN_NAV_SAFE_MODAL_PROPS, SHELL_OVERLAY_PROPS } from "@/shared/ui/shellPanelStyles";
import { AdminOwnerSubscriptionStrip } from "@/admin/components/AdminOwnerSubscriptionStrip";
import { useTranslation } from "react-i18next";
import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";

const NAVBAR_COLLAPSED_KEY = "admin_navbar_collapsed";
const PERM_LEADS_LOG_VIEW = "leads.log.view";

function MobileNavBurger({
  opened,
  onToggle,
  openLabel,
  closeLabel,
}: {
  opened: boolean;
  onToggle: () => void;
  openLabel: string;
  closeLabel: string;
}) {
  return (
    <ActionIcon
      variant="subtle"
      color="gray"
      size="lg"
      onClick={onToggle}
      title={opened ? closeLabel : openLabel}
      aria-label={opened ? closeLabel : openLabel}
    >
      <IconMenu2 size={22} />
    </ActionIcon>
  );
}

type NavGroupId = "staff" | "clients" | "business" | "system";
type NavItemLabelKey = `items.${keyof typeof enNav.items}`;

type NavItem = {
  to: string;
  labelKey: NavItemLabelKey;
  icon: React.ComponentType<Record<string, unknown>>;
  badgeKey?: string;
  /** owner role only (SaaS subscription, etc.). */
  ownerOnly?: boolean;
};

const navGroups: { id: NavGroupId; items: NavItem[] }[] = [
  {
    id: "staff",
    items: [
      { to: ROUTE_PATHS.admin.dashboard, labelKey: "items.feed", icon: IconDashboard },
      { to: ROUTE_PATHS.admin.staffChat, labelKey: "items.staffChat", icon: IconMessageCircle },
      { to: ROUTE_PATHS.admin.staffCalendar, labelKey: "items.staffCalendar", icon: IconCalendarEvent },
      { to: ROUTE_PATHS.admin.tasks, labelKey: "items.tasks", icon: IconListCheck },
      { to: ROUTE_PATHS.admin.leadsLog, labelKey: "items.leadsLog", icon: IconListCheck },
      { to: ROUTE_PATHS.admin.knowledge, labelKey: "items.knowledge", icon: IconBook },
    ],
  },
  {
    id: "clients",
    items: [
      { to: ROUTE_PATHS.admin.schedule, labelKey: "items.schedule", icon: IconCalendar },
      {
        to: ROUTE_PATHS.admin.omniChat,
        labelKey: "items.omniChat",
        icon: IconBrandWhatsapp,
        badgeKey: "omni-waiting",
      },
    ],
  },
  {
    id: "business",
    items: [
      { to: ROUTE_PATHS.admin.sales, labelKey: "items.sales", icon: IconBriefcase },
      { to: ROUTE_PATHS.admin.finance, labelKey: "items.finance", icon: IconCash },
      { to: ROUTE_PATHS.admin.commerce, labelKey: "items.commerce", icon: IconShoppingCart },
      { to: ROUTE_PATHS.admin.loyalty, labelKey: "items.loyalty", icon: IconGift },
      { to: ROUTE_PATHS.admin.reports, labelKey: "items.reports", icon: IconChartBar },
      { to: ROUTE_PATHS.admin.bookings, labelKey: "items.bookings", icon: IconClipboardList },
      { to: ROUTE_PATHS.admin.prepayment, labelKey: "items.prepayment", icon: IconReceipt },
      { to: ROUTE_PATHS.admin.waitlist, labelKey: "items.waitlist", icon: IconListSearch },
      { to: ROUTE_PATHS.admin.recall, labelKey: "items.recall", icon: IconRefresh },
      { to: ROUTE_PATHS.admin.marketing, labelKey: "items.marketing", icon: IconChartBar },
      { to: ROUTE_PATHS.admin.retention, labelKey: "items.retention", icon: IconTarget },
    ],
  },
  {
    id: "system",
    items: [
      { to: ROUTE_PATHS.admin.settings, labelKey: "items.settings", icon: IconSettings },
      {
        to: ROUTE_PATHS.admin.subscription,
        labelKey: "items.subscription",
        icon: IconCoin,
        ownerOnly: true,
      },
      { to: ROUTE_PATHS.admin.embed, labelKey: "items.embed", icon: IconCode },
      { to: ROUTE_PATHS.admin.ragKb, labelKey: "items.ragKb", icon: IconDatabase },
      { to: ROUTE_PATHS.admin.dataExport, labelKey: "items.dataExport", icon: IconDownload },
      { to: ROUTE_PATHS.admin.me, labelKey: "items.me", icon: IconUser },
      { to: ROUTE_PATHS.admin.doctors, labelKey: "items.doctors", icon: IconStethoscope },
      { to: ROUTE_PATHS.admin.doctorSchedule, labelKey: "items.doctorSchedule", icon: IconCalendarWeek },
      { to: ROUTE_PATHS.admin.patients, labelKey: "items.patients", icon: IconUserCircle },
      { to: ROUTE_PATHS.admin.services, labelKey: "items.services", icon: IconClipboardList },
      { to: ROUTE_PATHS.admin.clinics, labelKey: "items.clinics", icon: IconBuilding },
      { to: ROUTE_PATHS.admin.administrators, labelKey: "items.administrators", icon: IconShield },
      { to: ROUTE_PATHS.admin.rightsPolicies, labelKey: "items.rightsPolicies", icon: IconShield },
    ],
  },
];

function navGroupsVisible(
  groups: typeof navGroups,
  canPatientsPii: boolean,
  canRbacManage: boolean,
  canLeadsLogView: boolean,
  isOwner: boolean,
): typeof navGroups {
  return groups.map((g) => ({
    ...g,
    items: g.items.filter((item) => {
      if ("to" in item && item.to === ROUTE_PATHS.admin.patients && !canPatientsPii) return false;
      if ("to" in item && item.to === ROUTE_PATHS.admin.rightsPolicies && !canRbacManage) return false;
      if ("to" in item && item.to === ROUTE_PATHS.admin.leadsLog && !canLeadsLogView) return false;
      if ("ownerOnly" in item && item.ownerOnly && !isOwner) return false;
      return true;
    }),
  }));
}

function navGroupsForBoxEdition(
  groups: typeof navGroups,
  box: boolean,
): typeof navGroups {
  if (!box) return groups;
  const hidden = new Set(BOX_HIDDEN_ADMIN_PATHS);
  return groups.map((g) => ({
    ...g,
    items: g.items.filter((item) => !("to" in item && hidden.has(item.to))),
  }));
}

function navGroupsForEntitlements(
  groups: typeof navGroups,
  enforced: boolean,
  keys: string[] | undefined,
): typeof navGroups {
  if (!enforced || !keys?.length) return groups;
  return groups.map((g) => ({
    ...g,
    items: g.items.filter((item) => {
      if (!("to" in item)) return true;
      const need = ADMIN_NAV_PATH_ENTITLEMENT_KEY[item.to];
      if (!need) return true;
      return keys.includes(need);
    }),
  }));
}

export default function AdminLayout() {
  const { t } = useTranslation("nav");
  const { t: tc } = useTranslation("common");
  const location = useLocation();
  const omniChatFullWidth = location.pathname.startsWith(ROUTE_PATHS.admin.omniChat);
  const navigate = useNavigate();
  const {
    selectableClinics,
    currentClinicId,
    setCurrentClinicId,
    isClinicScopeLocked,
    error: clinicsError,
    isLoading,
  } = useAdminClinic();
  const { data: omniWaitingData } = useAdminOmniChats({
    status: "WAITING_FOR_OPERATOR",
    page: 1,
    page_size: 50,
  });
  const omniWaitingCount = omniWaitingData?.items.length ?? 0;

  const [navbarCollapsed, setNavbarCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(NAVBAR_COLLAPSED_KEY) === "true";
  });
  const isNarrowShell = useMediaQuery("(max-width: 48em)", false, {
    getInitialValueInEffect: false,
  });
  const [mobileNavOpened, setMobileNavOpened] = useState(false);
  useEffect(() => {
    setMobileNavOpened(false);
  }, [location.pathname]);
  const toggleNavbar = useCallback(() => {
    setNavbarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(NAVBAR_COLLAPSED_KEY, String(next));
      return next;
    });
  }, []);

  const { data: adminSession } = useAdminSession();
  const canPatientsPii =
    adminSession?.permissions?.includes(ADMIN_PERM_PATIENTS_PII_READ) ?? false;
  const canRbacManage =
    adminSession?.permissions?.includes(ADMIN_PERM_RBAC_MANAGE) ?? false;
  const canLeadsLogView = adminSession?.permissions?.includes(PERM_LEADS_LOG_VIEW) ?? false;
  const isOwner = adminSession?.roles?.includes("owner") ?? false;
  const boxEdition = isBoxEdition();
  const entEnforced = adminSession?.entitlement_enforced ?? false;
  const entKeys = adminSession?.entitlement_keys;
  const sidebarNavGroups = useMemo(
    () =>
      navGroupsForEntitlements(
        navGroupsForBoxEdition(
          navGroupsVisible(
            navGroups,
            canPatientsPii,
            canRbacManage,
            canLeadsLogView,
            isOwner,
          ),
          boxEdition,
        ),
        entEnforced,
        entKeys,
      ),
    [canPatientsPii, canRbacManage, canLeadsLogView, isOwner, boxEdition, entEnforced, entKeys],
  );

  const clinicOptions =
    selectableClinics.map((c) => ({
      value: c.id,
      label: c.name,
    })) ?? [];

  const [spotlightQuery, setSpotlightQuery] = useState("");
  const [askAiOpen, setAskAiOpen] = useState(false);
  const [aiQuestion, setAiQuestion] = useState("");
  const { data: searchData } = useAdminSearch(
    spotlightQuery.trim().length >= 2 ? spotlightQuery.trim() : null
  );
  const aiAgent = useAiAgent();
  const aiFeatures = useAiFeatures(currentClinicId ?? null);
  const spotlightFeature = aiFeatures.get("omni.spotlight.agent");

  const navActions: SpotlightActionData[] = useMemo(() => {
    const list: SpotlightActionData[] = [];
    sidebarNavGroups.forEach((group) => {
      group.items.forEach((item) => {
        if ("to" in item && item.to) {
          const Icon = item.icon;
          list.push({
            id: item.to,
            label: t(item.labelKey),
            description: t(`groups.${group.id}`),
            leftSection: <Icon size={20} stroke={1.5} />,
            onClick: () => navigate(item.to),
          });
        }
      });
    });
    return list;
  }, [navigate, sidebarNavGroups, t]);

  const askAiAction: SpotlightActionData = useMemo(
    () => ({
      id: "ask-ai",
      label: tc("spotlight.askAi"),
      description: tc("spotlight.askAiDescription", {
        status: getAiFeatureStatusText(spotlightFeature.status),
      }),
      leftSection: <IconRobot size={20} stroke={1.5} />,
      onClick: () => {
        spotlight.close();
        void logUiEvent({
          event_name: "ai_spotlight_open",
          clinic_id: currentClinicId,
          feature_id: spotlightFeature.id,
          feature_status: spotlightFeature.status,
        });
        setAskAiOpen(true);
      },
    }),
    [spotlightFeature.status, spotlightFeature.id, currentClinicId, tc]
  );

  const searchHitActions: SpotlightActionData[] = useMemo(() => {
    const items = searchData?.items ?? [];
    return items.map((hit) => ({
      id: `search-${hit.type}-${hit.id}`,
      label: hit.label,
      description: hit.description ?? (hit.type === "patient" ? tc("spotlight.patient") : tc("spotlight.booking")),
      leftSection:
        hit.type === "patient" ? (
          <IconUser size={20} stroke={1.5} />
        ) : (
          <IconCalendarEvent size={20} stroke={1.5} />
        ),
      onClick: () => navigate(hit.to),
    }));
  }, [searchData?.items, navigate, tc]);

  const spotlightActions: SpotlightActionData[] = useMemo(
    () => [askAiAction, ...searchHitActions, ...navActions],
    [askAiAction, searchHitActions, navActions]
  );

  const navbarWidth = navbarCollapsed ? 80 : 260;
  const sidebarStyles = {
    backgroundColor: "var(--admin-sidebar-bg)",
    borderRight: "1px solid var(--admin-sidebar-border)",
    color: "var(--admin-sidebar-text)",
  };

  return (
    <PersonCardProvider>
      <AppShell
        navbar={{
          width: navbarWidth,
          breakpoint: "sm",
          collapsed: { mobile: !mobileNavOpened, desktop: false },
        }}
        header={isNarrowShell ? { height: 52 } : undefined}
        padding={omniChatFullWidth ? 0 : "md"}
        styles={
          omniChatFullWidth
            ? {
                root: { minHeight: "100dvh", maxHeight: "100dvh", display: "flex" },
                main: { flex: 1, minHeight: 0, display: "flex", flexDirection: "column" },
              }
            : undefined
        }
      >
        <PersonCardModalHost />
        <AppShell.Navbar
          p="sm"
          h="100%"
          style={{
            ...sidebarStyles,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            zIndex: "var(--z-admin-navbar)",
          }}
          withBorder={false}
        >
          {/* Spotlight: Cmd+K / Ctrl+K; sections plus patient/booking hits when the API is up; Ask AI */}
          <Spotlight
            actions={spotlightActions}
            shortcut={["mod + K"]}
            nothingFound={tc("spotlight.nothingFound")}
            query={spotlightQuery}
            onQueryChange={setSpotlightQuery}
            searchProps={{
              placeholder: tc("spotlight.placeholder"),
              leftSection: <IconSearch size={20} stroke={1.5} />,
            }}
            limit={12}
          />

        {/* Top: clinic selector + links */}
        <Box mb="md" style={{ flexShrink: 0 }}>
          {!navbarCollapsed && (
            <Stack gap="xs">
              {isLoading ? (
                <Text size="xs" c="dimmed">{tc("clinics.loading")}</Text>
              ) : (
                <Select
                  size="xs"
                  radius="md"
                  data={clinicOptions}
                  value={currentClinicId}
                  onChange={setCurrentClinicId}
                  placeholder={clinicOptions.length ? undefined : tc("clinics.empty")}
                  w="100%"
                  disabled={isClinicScopeLocked && clinicOptions.length <= 1}
                  title={
                    isClinicScopeLocked
                      ? tc("clinics.jwtLockedTitle")
                      : undefined
                  }
                  styles={{
                    input: {
                      backgroundColor: "var(--bg-card)",
                      borderColor: "var(--admin-sidebar-border)",
                      color: "var(--text-main)",
                    },
                    dropdown: { zIndex: 2000 },
                    section: { color: "var(--admin-sidebar-text-muted)" },
                  }}
                  comboboxProps={{ withinPortal: true }}
                  nothingFoundMessage={tc("clinics.empty")}
                />
              )}
              <UnstyledButton
                type="button"
                onClick={() => spotlight.open()}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  width: "100%",
                  padding: "6px 8px",
                  borderRadius: 6,
                  color: "var(--admin-sidebar-text-muted)",
                  fontSize: 12,
                }}
              >
                <IconSearch size={16} />
                <span>{tc("spotlight.searchButton")}</span>
              </UnstyledButton>
              <Group gap="xs" wrap="nowrap">
                <Anchor component={Link} to="/" size="xs" c="dimmed">
                  {tc("home")}
                </Anchor>
                <Anchor
                  size="xs"
                  c="dimmed"
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    clearAdminToken();
                    navigate(ROUTE_PATHS.admin.login);
                  }}
                >
                  {tc("logout")}
                </Anchor>
              </Group>
            </Stack>
          )}
          {navbarCollapsed && (
            <Stack gap="xs" align="center">
              <Anchor component={Link} to="/" title={tc("home")} c="dimmed">
                <IconHome2 size={20} />
              </Anchor>
              <Anchor
                href="#"
                title={tc("logout")}
                c="dimmed"
                onClick={(e) => {
                  e.preventDefault();
                  clearAdminToken();
                  navigate(ROUTE_PATHS.admin.login);
                }}
              >
                <IconDoorExit size={20} />
              </Anchor>
            </Stack>
          )}
        </Box>

        {/* Nav list scrolls; collapse control stays pinned at the bottom */}
        <ScrollArea
          flex={1}
          type="scroll"
          scrollbarSize={6}
          offsetScrollbars
          style={{ minHeight: 0 }}
        >
          <Stack gap={6} pr={4}>
            {sidebarNavGroups.map((group) => (
              <Box key={group.id}>
                {!navbarCollapsed && (
                  <Text
                    size="xs"
                    tt="uppercase"
                    fw={600}
                    mb={4}
                    style={{ color: "var(--admin-sidebar-text-muted)" }}
                  >
                    {t(`groups.${group.id}`)}
                  </Text>
                )}
                <Stack gap={2}>
                  {group.items.map((item) => {
                  const linkItem = item;
                  const Icon = linkItem.icon;
                  const isActive = location.pathname === linkItem.to;
                  const showBadge =
                    linkItem.badgeKey === "omni-waiting" && omniWaitingCount > 0;
                  const badgeValue = omniWaitingCount;
                  return (
                    <Anchor
                      className="admin-nav-link"
                      data-active={isActive || undefined}
                      key={linkItem.to}
                      component={Link}
                      to={linkItem.to}
                      title={t(linkItem.labelKey)}
                      size="sm"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: navbarCollapsed ? "center" : "space-between",
                        gap: 8,
                        borderRadius: 8,
                        padding: navbarCollapsed ? 10 : "8px 10px",
                        fontWeight: isActive ? 600 : 500,
                        textDecoration: "none",
                        color: isActive
                          ? "var(--admin-nav-active-text)"
                          : "var(--admin-sidebar-text)",
                      }}
                    >
                      <Icon size={20} />
                      {!navbarCollapsed && (
                        <>
                          <span style={{ flex: 1, textAlign: "left" }}>{t(linkItem.labelKey)}</span>
                          {showBadge && (
                            <Badge size="xs" variant="dot" color="red">
                              {badgeValue > 99 ? "99+" : badgeValue}
                            </Badge>
                          )}
                        </>
                      )}
                    </Anchor>
                  );
                  })}
                </Stack>
              </Box>
            ))}
          </Stack>
        </ScrollArea>

        {/* Collapse button at bottom; locale switch fits only when the rail is 260px */}
        <Box
          pt="sm"
          style={{
            flexShrink: 0,
            borderTop: "1px solid var(--admin-sidebar-border)",
            backgroundColor: "var(--admin-sidebar-footer-bg)",
          }}
        >
          {!navbarCollapsed && !isNarrowShell ? (
            <Box mb="xs" px={4}>
              <UiLocaleSwitch />
            </Box>
          ) : null}
          <Group justify="center">
            <ActionIcon
              variant="subtle"
              color="gray"
              size="lg"
              onClick={toggleNavbar}
              title={navbarCollapsed ? tc("expandMenu") : tc("collapseMenu")}
              style={{ color: "var(--admin-sidebar-text-muted)" }}
            >
              {navbarCollapsed ? (
                <IconChevronRight size={22} />
              ) : (
                <IconChevronLeft size={22} />
              )}
            </ActionIcon>
          </Group>
        </Box>
      </AppShell.Navbar>

      {isNarrowShell ? (
      <AppShell.Header
        px="sm"
        withBorder
        style={{
          zIndex: "var(--z-admin-header)",
          backgroundColor: "var(--mantine-color-gray-0)",
        }}
      >
        <Group h="100%" justify="space-between" wrap="nowrap">
          <MobileNavBurger
            opened={mobileNavOpened}
            onToggle={() => setMobileNavOpened((open) => !open)}
            openLabel={tc("openSidebar")}
            closeLabel={tc("closeSidebar")}
          />
          <UiLocaleSwitch />
        </Group>
      </AppShell.Header>
      ) : null}

      <AppShell.Main
        style={{
          backgroundColor: "var(--mantine-color-gray-0)",
          ...(omniChatFullWidth
            ? { display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }
            : {}),
        }}
      >
        {omniChatFullWidth ? (
          <>
            {navbarCollapsed && !isNarrowShell ? (
              <Group justify="flex-end" wrap="wrap" gap="xs" px="md" pt="xs" pb={4} style={{ flexShrink: 0 }}>
                <UiLocaleSwitch />
              </Group>
            ) : null}
            {clinicsError ? (
              <Alert m="md" color="red" title={tc("clinics.loadErrorTitle")}>
                {tc("clinics.loadErrorBody")}
              </Alert>
            ) : null}
            <Box style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <Outlet />
            </Box>
          </>
        ) : (
          <Container size="xl" py="md">
            {navbarCollapsed && !isNarrowShell ? (
              <Group justify="flex-end" wrap="wrap" gap="xs" mb="sm">
                <UiLocaleSwitch />
              </Group>
            ) : null}
            {clinicsError ? (
              <Alert mb="md" color="red" title={tc("clinics.loadErrorTitle")}>
                {tc("clinics.loadErrorBody")}
              </Alert>
            ) : null}
            {location.pathname !== ROUTE_PATHS.admin.subscription ? (
              <AdminOwnerSubscriptionStrip />
            ) : null}
            <Paper
              radius="md"
              p="md"
              withBorder
              shadow="sm"
              style={{ border: "1px solid var(--mantine-color-gray-2)" }}
            >
              <Outlet />
            </Paper>
          </Container>
        )}
      </AppShell.Main>

        {/* Ask AI (Spotlight) */}
        <Modal
          {...ADMIN_NAV_SAFE_MODAL_PROPS}
          overlayProps={SHELL_OVERLAY_PROPS}
          opened={askAiOpen}
          onClose={() => {
            setAskAiOpen(false);
            setAiQuestion("");
          }}
          title={
            <Group gap="xs" wrap="wrap">
              <Text fw={600}>{tc("spotlight.askAi")}</Text>
              <Badge
                size="sm"
                variant="light"
                color={getAiFeatureBadgeColor(spotlightFeature.status)}
                title={getAiFeatureTooltip(spotlightFeature.status)}
              >
                {getAiFeatureStatusText(spotlightFeature.status)}
              </Badge>
            </Group>
          }
          size="md"
          centered
        >
          <Stack gap="md">
            <Text size="xs" c="dimmed">
              {getAiFeatureTooltip(spotlightFeature.status)}
            </Text>
            <Textarea
              placeholder={tc("spotlight.questionPlaceholder")}
              value={aiQuestion}
              onChange={(e) => setAiQuestion(e.currentTarget.value)}
              minRows={3}
              autosize
            />
            <Group justify="flex-end">
              <Button
                variant="subtle"
                color={SEMANTIC.action.dismiss}
                onClick={() => {
                  setAskAiOpen(false);
                  setAiQuestion("");
                }}
              >
                {tc("cancel")}
              </Button>
              <Button
                color={SEMANTIC.ai.accent}
                loading={aiAgent.isPending}
                disabled={!aiQuestion.trim()}
                onClick={() => {
                  if (!aiQuestion.trim()) return;
                  void logUiEvent({
                    event_name: "ai_spotlight_send",
                    clinic_id: currentClinicId,
                    feature_id: spotlightFeature.id,
                    feature_status: spotlightFeature.status,
                  });
                  aiAgent.mutate({ query: aiQuestion.trim() });
                }}
              >
                {tc("send")}
              </Button>
            </Group>
            {aiAgent.data?.answer && (
              <Paper p="sm" withBorder radius="md" bg="gray.0">
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {aiAgent.data.answer}
                </Text>
              </Paper>
            )}
          </Stack>
        </Modal>
      </AppShell>
    </PersonCardProvider>
  );
}
