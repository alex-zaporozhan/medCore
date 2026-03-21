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
import { useAttentionFeed } from "@/hooks/useAttentionFeed";
import type { AttentionItem } from "@/api/types";
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
  IconDiscount,
  IconBell,
  IconFileText,
  IconBrandWhatsapp,
  IconPlug,
  IconPalette,
  IconMoodSmile,
  IconShield,
  IconCreditCard,
  IconBook,
  IconForms,
  IconAlertCircle,
  IconHome2,
  IconDoorExit,
  IconRobot,
  IconUser,
  IconCalendarEvent,
  IconTarget,
  IconPhoto,
} from "@tabler/icons-react";
import type { SpotlightActionData } from "@mantine/spotlight";
import { useAdminSearch } from "@/hooks/useAdminSearch";
import { useAiAgent } from "@/hooks/useAiAgent";
import { useAiFeatures, getAiFeatureBadgeColor, getAiFeatureStatusText, getAiFeatureTooltip } from "@/shared/aiFeatures";
import { logUiEvent } from "@/shared/uiEvents";
import { ROUTE_PATHS } from "@/routePaths";

const ATTENTION_BAR_STORAGE_KEY = "admin_attention_bar_visible";
const NAVBAR_COLLAPSED_KEY = "admin_navbar_collapsed";

type NavItem =
  | { to: string; label: string; icon: React.ComponentType<Record<string, unknown>>; badgeKey?: string }
  | { label: string; toggleAttentionBar: true };

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: "OPERATIONS",
    items: [
      { to: ROUTE_PATHS.admin.dashboard, label: "Dashboard", icon: IconDashboard },
      { to: ROUTE_PATHS.admin.schedule, label: "Schedule & Bookings", icon: IconCalendar },
      {
        to: ROUTE_PATHS.admin.omniChat,
        label: "Chat & AI",
        icon: IconMessageCircle,
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
      { to: ROUTE_PATHS.admin.tasks, label: "Tasks", icon: IconListCheck },
      { to: ROUTE_PATHS.admin.reports, label: "Analytics / Reports", icon: IconChartBar },
      { to: ROUTE_PATHS.admin.bookings, label: "Записи", icon: IconClipboardList },
      { to: ROUTE_PATHS.admin.prepayment, label: "Предоплата", icon: IconReceipt },
      { to: ROUTE_PATHS.admin.waitlist, label: "Очередь", icon: IconListSearch },
      { to: ROUTE_PATHS.admin.recall, label: "Recall", icon: IconRefresh },
      { to: ROUTE_PATHS.admin.marketing, label: "Маркетинг", icon: IconChartBar },
      { to: ROUTE_PATHS.admin.retention, label: "Retention", icon: IconTarget },
      { to: ROUTE_PATHS.admin.attention, label: "Лента внимания", icon: IconAlertCircle },
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
      { to: ROUTE_PATHS.admin.omniChannels, label: "Omni‑каналы", icon: IconBrandWhatsapp },
      { to: ROUTE_PATHS.admin.channels, label: "Каналы", icon: IconBrandWhatsapp },
      { to: ROUTE_PATHS.admin.integrations, label: "Интеграции", icon: IconPlug },
      { to: ROUTE_PATHS.admin.styling, label: "Стилизация", icon: IconPalette },
      { to: ROUTE_PATHS.admin.stickers, label: "Стикеры", icon: IconMoodSmile },
      { to: ROUTE_PATHS.admin.administrators, label: "Администраторы", icon: IconShield },
      { to: ROUTE_PATHS.admin.paymentGateway, label: "Платёжный шлюз", icon: IconCreditCard },
      { to: ROUTE_PATHS.admin.clientReference, label: "Справочник клиентов", icon: IconBook },
      { to: ROUTE_PATHS.admin.discounts, label: "Скидки и акции", icon: IconDiscount },
      { to: ROUTE_PATHS.admin.notificationPolicy, label: "Уведомления", icon: IconBell },
      { to: ROUTE_PATHS.admin.agreements, label: "Соглашения", icon: IconFileText },
      { to: ROUTE_PATHS.admin.forms, label: "Формы", icon: IconForms },
      { to: ROUTE_PATHS.admin.omniVault, label: "Omni-Vault", icon: IconPhoto },
      { label: "placeholder", toggleAttentionBar: true },
    ],
  },
];

function pickFirstAttentionItem(data: { follow_up: AttentionItem[]; retention_gap: AttentionItem[]; conflicts: AttentionItem[] } | undefined): AttentionItem | null {
  if (!data) return null;
  const openFollowUps = data.follow_up.filter((i) => i.status === "new");
  const all = [...openFollowUps, ...data.retention_gap, ...data.conflicts];
  const byPriority = [...all].sort((a, b) => a.priority - b.priority);
  return byPriority[0] ?? null;
}

export default function AdminLayout() {
  const location = useLocation();
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

  const [attentionBarVisible, setAttentionBarVisible] = useState(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem(ATTENTION_BAR_STORAGE_KEY) !== "false";
  });
  const toggleAttentionBar = useCallback(() => {
    setAttentionBarVisible((prev) => {
      const next = !prev;
      localStorage.setItem(ATTENTION_BAR_STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const { data: attentionFeedData } = useAttentionFeed(currentClinicId ?? null);
  const firstAttentionItem = useMemo(
    () => pickFirstAttentionItem(attentionFeedData),
    [attentionFeedData]
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
    navGroups.forEach((group) => {
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
  }, [navigate]);

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
      padding="md"
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
            {navGroups.map((group, gi) => (
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
                    if ("toggleAttentionBar" in item && item.toggleAttentionBar) {
                      if (navbarCollapsed) return null;
                      return (
                        <UnstyledButton
                          key="attention-bar-toggle"
                          type="button"
                          onClick={toggleAttentionBar}
                          w="100%"
                          py={8}
                          px={10}
                          style={{
                            borderRadius: 8,
                            color: "var(--admin-sidebar-text-muted)",
                          }}
                        >
                          <Text component="span" size="sm" fw={500} lineClamp={2}>
                            {attentionBarVisible
                              ? "Скрыть ленту внимания"
                              : "Показать ленту внимания"}
                          </Text>
                        </UnstyledButton>
                      );
                    }
                  const linkItem = item as { to: string; label: string; icon: React.ComponentType<Record<string, unknown>>; badgeKey?: string };
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
                        color: "var(--admin-sidebar-text)",
                      }}
                    >
                      <Icon size={20} />
                      {!navbarCollapsed && (
                        <>
                          <span style={{ flex: 1, textAlign: "left" }}>{linkItem.label}</span>
                          {showBadge && (
                            <Badge size="sm" variant="filled" color="red" circle>
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

      <AppShell.Main style={{ backgroundColor: "var(--bg-main)" }}>
        <Container size="xl" py="md">
          {attentionBarVisible && firstAttentionItem && (
            <Box
              mb="md"
              py="xs"
              px="md"
              style={{
                borderRadius: 8,
                backgroundColor: "var(--mantine-color-indigo-0)",
                border: "1px solid var(--mantine-color-indigo-2)",
              }}
            >
              <Group justify="space-between" wrap="nowrap">
                <Text size="sm" lineClamp={1} style={{ flex: 1 }}>
                  {firstAttentionItem.title}
                  {firstAttentionItem.description ? ` — ${firstAttentionItem.description}` : ""}
                </Text>
                <Anchor
                  component={Link}
                  to={
                    firstAttentionItem.conversation_id
                      ? `${ROUTE_PATHS.admin.omniChat}?conversation=${firstAttentionItem.conversation_id}`
                      : ROUTE_PATHS.admin.attention
                  }
                  size="sm"
                  fw={500}
                >
                  Перейти
                </Anchor>
              </Group>
            </Box>
          )}
          {clinicsError ? (
            <Alert mb="md" color="red" title="Ошибка загрузки данных">
              Не удалось загрузить список клиник. Убедитесь, что бэкенд запущен (порт 8000). Подробнее: docs/RUN_SERVICES.md
            </Alert>
          ) : null}
          <Paper
            radius="xl"
            p="md"
            withBorder
            style={{ border: "1px solid var(--mantine-color-gray-2)" }}
          >
            <Outlet />
          </Paper>
        </Container>
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
              onClick={() => {
                setAskAiOpen(false);
                setAiQuestion("");
              }}
            >
              Отмена
            </Button>
            <Button
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
