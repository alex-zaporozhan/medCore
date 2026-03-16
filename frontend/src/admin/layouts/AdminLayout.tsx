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

const ATTENTION_BAR_STORAGE_KEY = "admin_attention_bar_visible";
const NAVBAR_COLLAPSED_KEY = "admin_navbar_collapsed";

type NavItem =
  | { to: string; label: string; icon: React.ComponentType<Record<string, unknown>>; badgeKey?: string }
  | { label: string; toggleAttentionBar: true };

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: "OPERATIONS",
    items: [
      { to: "/admin", label: "Dashboard", icon: IconDashboard },
      { to: "/admin/schedule", label: "Schedule & Bookings", icon: IconCalendar },
      { to: "/admin/omni-chat", label: "Chat & AI", icon: IconMessageCircle, badgeKey: "omni-waiting" },
    ],
  },
  {
    title: "BUSINESS",
    items: [
      { to: "/admin/sales", label: "CRM & Sales", icon: IconBriefcase },
      { to: "/admin/finance", label: "Finance", icon: IconCash },
      { to: "/admin/loyalty", label: "Loyalty", icon: IconGift },
      { to: "/admin/tasks", label: "Tasks", icon: IconListCheck },
      { to: "/admin/reports", label: "Analytics / Reports", icon: IconChartBar },
      { to: "/admin/bookings", label: "Записи", icon: IconClipboardList },
      { to: "/admin/prepayment", label: "Предоплата", icon: IconReceipt },
      { to: "/admin/waitlist", label: "Очередь", icon: IconListSearch },
      { to: "/admin/recall", label: "Recall", icon: IconRefresh },
      { to: "/admin/marketing", label: "Маркетинг", icon: IconChartBar },
      { to: "/admin/retention", label: "Retention", icon: IconTarget },
      { to: "/admin/attention", label: "Лента внимания", icon: IconAlertCircle },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { to: "/admin/settings", label: "Настройки", icon: IconSettings },
      { to: "/admin/doctors", label: "Врачи", icon: IconStethoscope },
      { to: "/admin/doctor-schedule", label: "Расписание врачей", icon: IconCalendarWeek },
      { to: "/admin/patients", label: "Пациенты", icon: IconUserCircle },
      { to: "/admin/services", label: "Услуги", icon: IconClipboardList },
      { to: "/admin/clinics", label: "Клиники", icon: IconBuilding },
      { to: "/admin/omni-channels", label: "Omni‑каналы", icon: IconBrandWhatsapp },
      { to: "/admin/channels", label: "Каналы", icon: IconBrandWhatsapp },
      { to: "/admin/integrations", label: "Интеграции", icon: IconPlug },
      { to: "/admin/styling", label: "Стилизация", icon: IconPalette },
      { to: "/admin/stickers", label: "Стикеры", icon: IconMoodSmile },
      { to: "/admin/administrators", label: "Администраторы", icon: IconShield },
      { to: "/admin/payment-gateway", label: "Платёжный шлюз", icon: IconCreditCard },
      { to: "/admin/client-reference", label: "Справочник клиентов", icon: IconBook },
      { to: "/admin/discounts", label: "Скидки и акции", icon: IconDiscount },
      { to: "/admin/notification-policy", label: "Уведомления", icon: IconBell },
      { to: "/admin/agreements", label: "Соглашения", icon: IconFileText },
      { to: "/admin/forms", label: "Формы", icon: IconForms },
      { to: "/admin/omni-vault", label: "Omni-Vault", icon: IconPhoto },
      { label: "placeholder", toggleAttentionBar: true },
    ],
  },
];

function pickFirstAttentionItem(data: { follow_up: AttentionItem[]; retention_gap: AttentionItem[]; conflicts: AttentionItem[] } | undefined): AttentionItem | null {
  if (!data) return null;
  const openFollowUps = data.follow_up.filter((i) => i.status === "open");
  const all = [...openFollowUps, ...data.retention_gap, ...data.conflicts];
  const byPriority = [...all].sort((a, b) => a.priority - b.priority);
  return byPriority[0] ?? null;
}

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { clinics, currentClinicId, setCurrentClinicId, error: clinicsError, isLoading } = useAdminClinic();
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
    clinics.map((c) => ({
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
      description: "Задать вопрос AI-ассистенту",
      leftSection: <IconRobot size={20} stroke={1.5} />,
      onClick: () => {
        spotlight.close();
        setAskAiOpen(true);
      },
    }),
    []
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
    backgroundColor: "var(--mantine-color-dark-8)",
    borderRight: "1px solid var(--mantine-color-dark-6)",
    color: "var(--mantine-color-gray-3)",
  };

  return (
    <AppShell
      navbar={{ width: navbarWidth, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Navbar
        p="sm"
        style={{
          ...sidebarStyles,
          overflowY: "auto",
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
        <Box mb="md">
          {!navbarCollapsed && (
            <Stack gap="xs">
              {isLoading ? (
                <Text size="xs" c="gray.4">Загрузка клиник...</Text>
              ) : (
                <Select
                  size="xs"
                  radius="md"
                  data={clinicOptions}
                  value={currentClinicId}
                  onChange={setCurrentClinicId}
                  placeholder={clinicOptions.length ? undefined : "Нет клиник"}
                  w="100%"
                  styles={{
                    input: {
                      backgroundColor: "rgba(255,255,255,0.1)",
                      borderColor: "rgba(255,255,255,0.2)",
                      color: "var(--mantine-color-gray-3)",
                    },
                    dropdown: { zIndex: 2000 },
                    section: { color: "var(--mantine-color-gray-4)" },
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
                  color: "var(--mantine-color-gray-5)",
                  fontSize: 12,
                }}
              >
                <IconSearch size={16} />
                <span>Поиск... (⌘K)</span>
              </UnstyledButton>
              <Group gap="xs" wrap="nowrap">
                <Anchor component={Link} to="/" size="xs" c="gray.4">
                  На главную
                </Anchor>
                <Anchor
                  size="xs"
                  c="gray.4"
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    clearAdminToken();
                    navigate("/admin/login");
                  }}
                >
                  Выйти
                </Anchor>
              </Group>
            </Stack>
          )}
          {navbarCollapsed && (
            <Stack gap="xs" align="center">
              <Anchor component={Link} to="/" title="На главную" c="gray.4">
                <IconHome2 size={20} />
              </Anchor>
              <Anchor
                href="#"
                title="Выйти"
                c="gray.4"
                onClick={(e) => {
                  e.preventDefault();
                  clearAdminToken();
                  navigate("/admin/login");
                }}
              >
                <IconDoorExit size={20} />
              </Anchor>
            </Stack>
          )}
        </Box>

        {/* Menu groups — flex: 1 so collapse button stays at bottom */}
        <Stack gap={6} style={{ flex: 1, minHeight: 0 }}>
          {navGroups.map((group, gi) => (
            <Box key={gi}>
              {!navbarCollapsed && (
                <Text size="xs" tt="uppercase" c="gray.5" fw={600} mb={4}>
                  {group.title}
                </Text>
              )}
              <Stack gap={2}>
                {group.items.map((item) => {
                  if ("toggleAttentionBar" in item && item.toggleAttentionBar) {
                    if (navbarCollapsed) return null;
                    return (
                      <Box
                        key="attention-bar-toggle"
                        component="button"
                        type="button"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          borderRadius: 8,
                          padding: "8px 10px",
                          fontWeight: 500,
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          color: "var(--mantine-color-gray-4)",
                          width: "100%",
                          textAlign: "left",
                          font: "inherit",
                        }}
                        onClick={toggleAttentionBar}
                      >
                        <span>
                          {attentionBarVisible
                            ? "Скрыть ленту внимания"
                            : "Показать ленту внимания"}
                        </span>
                      </Box>
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
                        color: isActive ? "white" : "var(--mantine-color-gray-4)",
                        backgroundColor: isActive ? "var(--mantine-color-indigo-6)" : "transparent",
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

        {/* Collapse button at bottom */}
        <Box pt="sm" style={{ borderTop: "1px solid var(--mantine-color-dark-6)" }}>
          <Group justify="center">
            <ActionIcon
              variant="subtle"
              color="gray"
              size="lg"
              onClick={toggleNavbar}
              title={navbarCollapsed ? "Развернуть меню" : "Свернуть меню"}
              style={{ color: "var(--mantine-color-gray-4)" }}
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

      <AppShell.Main style={{ backgroundColor: "var(--mantine-color-gray-0)" }}>
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
                      ? `/admin/omni-chat?conversation=${firstAttentionItem.conversation_id}`
                      : "/admin/attention"
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
        title="Спросить AI"
        size="md"
      >
        <Stack gap="md">
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
