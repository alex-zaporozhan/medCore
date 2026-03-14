import {
  Alert,
  Anchor,
  AppShell,
  Badge,
  Box,
  Container,
  Group,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { useMemo, useState, useCallback } from "react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { clearAdminToken } from "@/api/client";
import { useAdminOmniChats } from "@/hooks/useAdminOmniChat";
import { useAttentionFeed } from "@/hooks/useAttentionFeed";
import type { AttentionItem } from "@/api/types";

const ATTENTION_BAR_STORAGE_KEY = "admin_attention_bar_visible";

type NavItem =
  | { to: string; label: string; badgeKey?: string }
  | { label: string; toggleAttentionBar: true };

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: "Business OS",
    items: [
      { to: "/admin", label: "Dashboard" },
      { to: "/admin/schedule", label: "Schedule & Bookings" },
      { to: "/admin/omni-chat", label: "Chat & AI", badgeKey: "omni-waiting" },
      { to: "/admin/sales", label: "CRM & Sales" },
      { to: "/admin/finance", label: "Finance & ERP" },
      { to: "/admin/loyalty", label: "Loyalty" },
      { to: "/admin/tasks", label: "Tasks" },
      { to: "/admin/reports", label: "Analytics" },
    ],
  },
  {
    title: "Operations & Patients",
    items: [
      { to: "/admin/bookings", label: "Записи" },
      { to: "/admin/waitlist", label: "Очередь" },
      { to: "/admin/recall", label: "Recall" },
      { to: "/admin/clinics", label: "Клиники" },
      { to: "/admin/doctors", label: "Врачи" },
      { to: "/admin/doctor-schedule", label: "График врачей" },
      { to: "/admin/patients", label: "Пациенты" },
      { to: "/admin/services", label: "Услуги" },
    ],
  },
  {
    title: "AI, Marketing & Paperless",
    items: [
      { to: "/admin/marketing", label: "Маркетинг" },
      { to: "/admin/forms", label: "Paperless / Формы" },
      { to: "/admin/agreements", label: "Согласия и договоры" },
      { to: "/admin/prepayment", label: "Предоплата" },
      { to: "/admin/discounts", label: "Скидки и акции" },
      { to: "/admin/attention", label: "Лента внимания" },
      { label: "placeholder", toggleAttentionBar: true },
    ],
  },
  {
    title: "Settings",
    items: [
      { to: "/admin/omni-channels", label: "Omni‑каналы" },
      { to: "/admin/omni-ai-settings", label: "AI‑настройки" },
      { to: "/admin/channels", label: "Каналы" },
      { to: "/admin/integrations", label: "Интеграции" },
      { to: "/admin/payment-gateway", label: "Платёжный шлюз" },
      { to: "/admin/notification-policy", label: "Уведомления" },
      { to: "/admin/styling", label: "Стили" },
      { to: "/admin/stickers", label: "Стикеры" },
      { to: "/admin/administrators", label: "Администраторы" },
      { to: "/admin/client-reference", label: "Справочник клиентов" },
      { to: "/admin/settings", label: "Общие настройки" },
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

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 260, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Header
        style={{
          backgroundColor: "var(--primary)",
          borderBottom: "1px solid var(--divider)",
        }}
      >
        <Group h="100%" px="lg" justify="space-between">
          <Group gap="md" align="center">
            <Text fw={700} c="var(--text-on-primary)">
              Админ-панель
            </Text>
            {isLoading ? (
              <Text size="xs" c="var(--text-on-primary)">
                Загрузка клиник...
              </Text>
            ) : (
              <Select
                size="xs"
                radius="xl"
                data={clinicOptions}
                value={currentClinicId}
                onChange={setCurrentClinicId}
                placeholder={clinicOptions.length ? undefined : "Нет клиник"}
                w={260}
                styles={{
                  input: {
                    backgroundColor: "rgba(255,255,255,0.14)",
                    borderColor: "rgba(255,255,255,0.3)",
                    color: "var(--text-on-primary)",
                    fontWeight: 500,
                  },
                  dropdown: {
                    zIndex: 2000,
                  },
                  section: {
                    color: "var(--text-on-primary)",
                  },
                }}
                comboboxProps={{ withinPortal: true }}
                nothingFoundMessage="Нет клиник"
              />
            )}
          </Group>
          <Group gap="md">
            <Anchor component={Link} to="/" size="sm" c="var(--text-on-primary)">
              На главную
            </Anchor>
            <Anchor
              size="sm"
              c="var(--text-on-primary)"
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
        </Group>
      </AppShell.Header>
      <AppShell.Navbar
        p="sm"
        style={{
          backgroundColor: "var(--bg-sidebar)",
          borderRight: "1px solid var(--divider)",
          boxShadow: "2px 0 12px rgba(0,0,0,0.04)",
          overflowY: "auto",
          paddingBottom: 16,
        }}
        withBorder={false}
      >
        <Stack gap={6}>
          {navGroups.map((group, gi) => (
            <Box
              key={gi}
              p={6}
              style={{
                borderRadius: 10,
                backgroundColor:
                  gi === 0
                    ? "rgba(59, 130, 246, 0.06)"
                    : gi === 1
                      ? "rgba(0, 0, 0, 0.02)"
                      : gi === 2
                        ? "rgba(34, 197, 94, 0.05)"
                        : gi === 3
                          ? "rgba(234, 179, 8, 0.05)"
                          : "rgba(0, 0, 0, 0.03)",
              }}
            >
              <Stack gap={2}>
                {group.items.map((item) => {
                  if ("toggleAttentionBar" in item && item.toggleAttentionBar) {
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
                          color: "inherit",
                          width: "100%",
                          textAlign: "left",
                          font: "inherit",
                        }}
                        onClick={toggleAttentionBar}
                      >
                        <span>
                          {attentionBarVisible
                            ? "Скрыть ленту внимания сверху"
                            : "Показывать ленту внимания сверху"}
                        </span>
                      </Box>
                    );
                  }
                  const linkItem = item as { to: string; label: string; badgeKey?: string };
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
                        justifyContent: "space-between",
                        borderRadius: 8,
                        padding: "8px 10px",
                        fontWeight: isActive ? 600 : 500,
                        textDecoration: "none",
                        color: "inherit",
                        ...(isActive
                          ? {
                              backgroundColor: "var(--primary-light, rgba(59, 130, 246, 0.14))",
                              color: "var(--primary)",
                            }
                          : {}),
                      }}
                    >
                      <span>{linkItem.label}</span>
                      {showBadge && (
                        <Badge size="sm" variant="filled" color="red" circle>
                          {badgeValue > 99 ? "99+" : badgeValue}
                        </Badge>
                      )}
                    </Anchor>
                  );
                })}
              </Stack>
            </Box>
          ))}
        </Stack>
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
                backgroundColor: "var(--primary-light, rgba(59, 130, 246, 0.08))",
                border: "1px solid var(--divider)",
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
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
