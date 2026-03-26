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
import { useMemo, useState, useCallback } from "react";
import { IconSearch } from "@tabler/icons-react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { clearAdminToken } from "@/api/client";
import { useAdminOmniChats } from "@/hooks/useAdminOmniChat";
import {
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
} from "@tabler/icons-react";
import type { SpotlightActionData } from "@mantine/spotlight";
import { useAdminSearch } from "@/hooks/useAdminSearch";
import { useAiAgent } from "@/hooks/useAiAgent";
import { useAiFeatures, getAiFeatureBadgeColor, getAiFeatureStatusText, getAiFeatureTooltip } from "@/shared/aiFeatures";
import { logUiEvent } from "@/shared/uiEvents";
import { ROUTE_PATHS } from "@/routePaths";
import { ADMIN_PERM_PATIENTS_PII_READ } from "@/shared/adminPermissions";
import { SEMANTIC } from "@/shared/semanticUi";
import { useAdminSession } from "@/hooks/useAdminSession";
import { BOX_HIDDEN_ADMIN_PATHS, isBoxEdition } from "@/config/edition";

const NAVBAR_COLLAPSED_KEY = "admin_navbar_collapsed";

type NavItem = {
  to: string;
  label: string;
  icon: React.ComponentType<Record<string, unknown>>;
  badgeKey?: string;
};

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: "СОТРУДНИКИ",
    items: [
      { to: ROUTE_PATHS.admin.dashboard, label: "Лента", icon: IconDashboard },
      { to: ROUTE_PATHS.admin.staffChat, label: "Мессенджер", icon: IconMessageCircle },
      { to: ROUTE_PATHS.admin.staffCalendar, label: "Календарь", icon: IconCalendarEvent },
      { to: ROUTE_PATHS.admin.tasks, label: "Задачи (Kanban)", icon: IconListCheck },
      { to: ROUTE_PATHS.admin.knowledge, label: "База знаний", icon: IconBook },
    ],
  },
  {
    title: "КЛИЕНТЫ",
    items: [
      { to: ROUTE_PATHS.admin.schedule, label: "Расписание", icon: IconCalendar },
      {
        to: ROUTE_PATHS.admin.omniChat,
        label: "Чат с клиентом",
        icon: IconBrandWhatsapp,
        badgeKey: "omni-waiting",
      },
    ],
  },
  {
    title: "BUSINESS",
    items: [
      { to: ROUTE_PATHS.admin.sales, label: "CRM & Sales", icon: IconBriefcase },
      { to: ROUTE_PATHS.admin.finance, label: "Finance", icon: IconCash },
      { to: ROUTE_PATHS.admin.loyalty, label: "Loyalty", icon: IconGift },
      { to: ROUTE_PATHS.admin.reports, label: "Analytics / Reports", icon: IconChartBar },
      { to: ROUTE_PATHS.admin.bookings, label: "Записи", icon: IconClipboardList },
      { to: ROUTE_PATHS.admin.prepayment, label: "Предоплата", icon: IconReceipt },
      { to: ROUTE_PATHS.admin.waitlist, label: "Очередь", icon: IconListSearch },
      { to: ROUTE_PATHS.admin.recall, label: "Recall", icon: IconRefresh },
      { to: ROUTE_PATHS.admin.marketing, label: "Маркетинг", icon: IconChartBar },
      { to: ROUTE_PATHS.admin.retention, label: "Retention", icon: IconTarget },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { to: ROUTE_PATHS.admin.settings, label: "Настройки", icon: IconSettings },
      { to: ROUTE_PATHS.admin.doctors, label: "Врачи", icon: IconStethoscope },
      { to: ROUTE_PATHS.admin.doctorSchedule, label: "Расписание врачей", icon: IconCalendarWeek },
      { to: ROUTE_PATHS.admin.patients, label: "Пациенты", icon: IconUserCircle },
      { to: ROUTE_PATHS.admin.services, label: "Услуги", icon: IconClipboardList },
      { to: ROUTE_PATHS.admin.clinics, label: "Клиники", icon: IconBuilding },
      { to: ROUTE_PATHS.admin.administrators, label: "Администраторы", icon: IconShield },
    ],
  },
];

function navGroupsVisible(
  groups: typeof navGroups,
  canPatientsPii: boolean,
): typeof navGroups {
  if (canPatientsPii) return groups;
  return groups.map((g) => ({
    ...g,
    items: g.items.filter((item) => {
      if ("to" in item && item.to === ROUTE_PATHS.admin.patients) return false;
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

export default function AdminLayout() {
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
  const boxEdition = isBoxEdition();
  const sidebarNavGroups = useMemo(
    () =>
      navGroupsForBoxEdition(navGroupsVisible(navGroups, canPatientsPii), boxEdition),
    [canPatientsPii, boxEdition],
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
            label: item.label,
            description: group.title,
            leftSection: <Icon size={20} stroke={1.5} />,
            onClick: () => navigate(item.to),
          });
        }
      });
    });
    return list;
  }, [navigate, sidebarNavGroups]);

  const askAiAction: SpotlightActionData = useMemo(
    () => ({
      id: "ask-ai",
      label: "Спросить AI",
      description: `Задать вопрос AI‑ассистенту (${getAiFeatureStatusText(spotlightFeature.status)})`,
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
    [spotlightFeature.status, spotlightFeature.id, currentClinicId]
  );

  const searchHitActions: SpotlightActionData[] = useMemo(() => {
    const items = searchData?.items ?? [];
    return items.map((hit) => ({
      id: `search-${hit.type}-${hit.id}`,
      label: hit.label,
      description: hit.description ?? (hit.type === "patient" ? "Пациент" : "Запись"),
      leftSection:
        hit.type === "patient" ? (
          <IconUser size={20} stroke={1.5} />
        ) : (
          <IconCalendarEvent size={20} stroke={1.5} />
        ),
      onClick: () => navigate(hit.to),
    }));
  }, [searchData?.items, navigate]);

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
    <AppShell
      navbar={{ width: navbarWidth, breakpoint: "sm" }}
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
      <AppShell.Navbar
        p="sm"
        h="100%"
        style={{
          ...sidebarStyles,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
        withBorder={false}
      >
        {/* Spotlight: Cmd+K / Ctrl+K; поиск по разделам и при API по пациентам/записям; «Спросить AI» */}
        <Spotlight
          actions={spotlightActions}
          shortcut={["mod + K"]}
          nothingFound="Ничего не найдено"
          query={spotlightQuery}
          onQueryChange={setSpotlightQuery}
          searchProps={{
            placeholder: "Поиск разделов, пациентов, записей... (⌘K)",
            leftSection: <IconSearch size={20} stroke={1.5} />,
          }}
          limit={12}
        />

        {/* Top: clinic selector + links */}
        <Box mb="md" style={{ flexShrink: 0 }}>
          {!navbarCollapsed && (
            <Stack gap="xs">
              {isLoading ? (
                <Text size="xs" c="dimmed">Загрузка клиник...</Text>
              ) : (
                <Select
                  size="xs"
                  radius="md"
                  data={clinicOptions}
                  value={currentClinicId}
                  onChange={setCurrentClinicId}
                  placeholder={clinicOptions.length ? undefined : "Нет клиник"}
                  w="100%"
                  disabled={isClinicScopeLocked && clinicOptions.length <= 1}
                  title={
                    isClinicScopeLocked
                      ? "Клиника совпадает с вашей учётной записью (JWT). Смена филиала — через отдельную роль/вход."
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
                  nothingFoundMessage="Нет клиник"
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
                <span>Поиск... (⌘K)</span>
              </UnstyledButton>
              <Group gap="xs" wrap="nowrap">
                <Anchor component={Link} to="/" size="xs" c="dimmed">
                  На главную
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
                  Выйти
                </Anchor>
              </Group>
            </Stack>
          )}
          {navbarCollapsed && (
            <Stack gap="xs" align="center">
              <Anchor component={Link} to="/" title="На главную" c="dimmed">
                <IconHome2 size={20} />
              </Anchor>
              <Anchor
                href="#"
                title="Выйти"
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

        {/* Только список разделов скроллится; кнопка «Свернуть» закреплена внизу навбара */}
        <ScrollArea
          flex={1}
          type="scroll"
          scrollbarSize={6}
          offsetScrollbars
          style={{ minHeight: 0 }}
        >
          <Stack gap={6} pr={4}>
            {sidebarNavGroups.map((group, gi) => (
              <Box key={gi}>
                {!navbarCollapsed && (
                  <Text
                    size="xs"
                    tt="uppercase"
                    fw={600}
                    mb={4}
                    style={{ color: "var(--admin-sidebar-text-muted)" }}
                  >
                    {group.title}
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
                          <span style={{ flex: 1, textAlign: "left" }}>{linkItem.label}</span>
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

        {/* Collapse button at bottom */}
        <Box
          pt="sm"
          style={{
            flexShrink: 0,
            borderTop: "1px solid var(--admin-sidebar-border)",
            backgroundColor: "var(--admin-sidebar-footer-bg)",
          }}
        >
          <Group justify="center">
            <ActionIcon
              variant="subtle"
              color="gray"
              size="lg"
              onClick={toggleNavbar}
              title={navbarCollapsed ? "Развернуть меню" : "Свернуть меню"}
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
            {clinicsError ? (
              <Alert m="md" color="red" title="Ошибка загрузки данных">
                Не удалось загрузить список клиник. Убедитесь, что бэкенд запущен (порт 8000). Подробнее: docs/RUN_SERVICES.md
              </Alert>
            ) : null}
            <Box style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <Outlet />
            </Box>
          </>
        ) : (
          <Container size="xl" py="md">
            {clinicsError ? (
              <Alert mb="md" color="red" title="Ошибка загрузки данных">
                Не удалось загрузить список клиник. Убедитесь, что бэкенд запущен (порт 8000). Подробнее: docs/RUN_SERVICES.md
              </Alert>
            ) : null}
            <Paper
              radius="md"
              p="md"
              withBorder
              shadow="sm"
              bg="#ffffff"
              style={{ border: "1px solid var(--mantine-color-gray-2)" }}
            >
              <Outlet />
            </Paper>
          </Container>
        )}
      </AppShell.Main>

      {/* Спросить AI (Spotlight → вкладка/режим по техпаспорту) */}
      <Modal
        opened={askAiOpen}
        onClose={() => {
          setAskAiOpen(false);
          setAiQuestion("");
        }}
        title={
          <Group gap="xs" wrap="wrap">
            <Text fw={600}>Спросить AI</Text>
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
      >
        <Stack gap="md">
          <Text size="xs" c="dimmed">
            {getAiFeatureTooltip(spotlightFeature.status)}
          </Text>
          <Textarea
            placeholder="Введите вопрос ассистенту..."
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
              Отмена
            </Button>
            <Button
              color={SEMANTIC.ai.accent}
              loading={aiAgent.isPending}
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
              Отправить
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
  );
}
