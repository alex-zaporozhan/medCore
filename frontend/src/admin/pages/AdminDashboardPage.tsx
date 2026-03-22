import { useAdminReportsDashboardByClinics } from "@/hooks/useAdminReports";
import { useAttentionFeed } from "@/hooks/useAttentionFeed";
import { useAdminBookings } from "@/hooks/useAdminBookings";
import { useRevenueHunterSaved, isRevenueHunterEnabled } from "@/hooks";
import { AdminDrawer, PageSkeleton, EmptyState, ContextBar, QueryErrorAlert } from "@/shared/ui";
import {
  Card,
  Grid,
  Group,
  MultiSelect,
  Stack,
  Text,
  Badge,
  Button,
  ScrollArea,
  ThemeIcon,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { useState, useMemo } from "react";
import { ROUTE_PATHS } from "@/routePaths";
import { SEMANTIC } from "@/shared/semanticUi";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import type { AttentionItem } from "@/api/types";
import type { Booking } from "@/api/types";
import { IconCalendar, IconCash, IconUsers, IconX, IconRobot } from "@tabler/icons-react";

const BACKEND_HINT =
  "Если данные не загружаются, проверьте, что бэкенд запущен на порту 8000 (см. docs/RUN_SERVICES.md).";

function flattenAttentionFeed(
  data: { follow_up: AttentionItem[]; retention_gap: AttentionItem[]; conflicts: AttentionItem[] } | undefined
): AttentionItem[] {
  if (!data) return [];
  const all = [
    ...data.follow_up.map((i) => ({ ...i, kind: "follow_up" as const })),
    ...data.retention_gap.map((i) => ({ ...i, kind: "retention_gap" as const })),
    ...data.conflicts.map((i) => ({ ...i, kind: "conflict" as const })),
  ];
  return all.sort((a, b) => a.priority - b.priority);
}

const KIND_LABEL: Record<string, string> = {
  follow_up: "Перезвонить",
  retention_gap: "Давно не был",
  conflict: "Конфликт",
};
const KIND_COLOR: Record<string, string> = {
  follow_up: "indigo",
  retention_gap: "yellow",
  conflict: "red",
};

const metricCardShell = {
  bg: "white" as const,
  styles: { root: { borderColor: "var(--mantine-color-gray-3)" } },
};

export default function AdminDashboardPage() {
  const { clinics, currentClinicId } = useAdminClinic();
  const [selectedClinicIds, setSelectedClinicIds] = useState<string[]>([]);
  const [timelineBooking, setTimelineBooking] = useState<Booking | null>(null);
  const today = dayjs().format("YYYY-MM-DD");

  const clinicOptions = clinics.map((c) => ({ value: c.id, label: c.name }));

  const { data: reportData, isLoading: reportLoading, isError: reportError, error: reportErr } =
    useAdminReportsDashboardByClinics(
      today,
      "day",
      selectedClinicIds.length > 0 ? selectedClinicIds : null
    );

  const { data: attentionData, isLoading: attentionLoading } = useAttentionFeed(currentClinicId ?? null);
  const { data: todayBookings, isLoading: bookingsLoading } = useAdminBookings({ date: today });
  const { data: revenueHunter } = useRevenueHunterSaved(currentClinicId ?? null);

  const attentionItems = useMemo(() => flattenAttentionFeed(attentionData), [attentionData]);
  const isLoading = reportLoading;
  const isError = reportError;
  const error = reportErr;

  if (isLoading) {
    return (
      <Stack gap="lg">
        <ContextBar title="Дашборд" />
        {clinics.length > 0 && (
          <MultiSelect
            label="Клиники"
            placeholder="Выберите одну или несколько клиник (пусто = все)"
            data={clinicOptions}
            value={selectedClinicIds}
            onChange={setSelectedClinicIds}
            searchable
            clearable
          />
        )}
        <Text size="sm" c="dimmed">
          {BACKEND_HINT}
        </Text>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col span={{ base: 12, md: 7 }}>
            <PageSkeleton variant="table" rows={4} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <PageSkeleton variant="table" rows={6} />
          </Grid.Col>
        </Grid>
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack gap="lg">
        <ContextBar title="Дашборд" />
        {clinics.length > 0 && (
          <MultiSelect
            label="Клиники"
            placeholder="Выберите одну или несколько клиник (пусто = все)"
            data={clinicOptions}
            value={selectedClinicIds}
            onChange={setSelectedClinicIds}
            searchable
            clearable
          />
        )}
        <QueryErrorAlert error={error} />
        <Text size="sm" c="dimmed">
          {BACKEND_HINT}
        </Text>
      </Stack>
    );
  }

  const data = reportData;
  const totalBookings =
    data != null
      ? data.bookings_pending + data.bookings_confirmed + data.bookings_completed
      : 0;

  return (
    <Stack gap="lg">
      <ContextBar title="Дашборд" />
      {clinics.length > 0 && (
        <MultiSelect
          label="Клиники"
          placeholder="Выберите одну или несколько клиник (пусто = все)"
          data={clinicOptions}
          value={selectedClinicIds}
          onChange={setSelectedClinicIds}
          searchable
          clearable
        />
      )}
      {data && (
        <Text size="sm" c="dimmed">
          {selectedClinicIds.length === 0
            ? `Сводка по всем клиникам за ${dayjs(data.date).format("DD.MM.YYYY")}`
            : `Сводка по выбранным клиникам (${selectedClinicIds.length}) за ${dayjs(data.date).format("DD.MM.YYYY")}`}
        </Text>
      )}

      {/* 4 метрики сверху */}
      <Grid>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card padding="md" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={4} wrap="nowrap">
              <ThemeIcon variant="light" color={SEMANTIC.metrics.appointments} size="lg" radius="md">
                <IconCalendar size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Записи сегодня
              </Text>
            </Group>
            <Text fw={700} fz="xl" c="gray.9">
              {totalBookings}
            </Text>
            {data && (
              <Text size="xs" c="dimmed" mt="xs">
                ожид. {data.bookings_pending} · подтв. {data.bookings_confirmed} · оказано {data.bookings_completed}
              </Text>
            )}
            <Text size="xs" c="dimmed" mt={2}>
              к вчера: —
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card padding="md" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={4} wrap="nowrap">
              <ThemeIcon variant="light" color={SEMANTIC.metrics.revenue} size="lg" radius="md">
                <IconCash size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Выручка
              </Text>
            </Group>
            <Text fw={700} fz="xl" c="gray.9">
              {data?.revenue ?? "0"} ₽
            </Text>
            <Text size="xs" c="dimmed" mt="xs">
              за день
            </Text>
            <Text size="xs" c="dimmed" mt={2}>
              к вчера: —
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card padding="md" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={4} wrap="nowrap">
              <ThemeIcon variant="light" color={SEMANTIC.metrics.patients} size="lg" radius="md">
                <IconUsers size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Новые пациенты
              </Text>
            </Group>
            <Text fw={700} fz="xl" c="gray.9">
              {data?.new_patients ?? 0}
            </Text>
            <Text size="xs" c="dimmed" mt="xs">
              за день
            </Text>
            <Text size="xs" c="dimmed" mt={2}>
              к вчера: —
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card padding="md" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={4} wrap="nowrap">
              <ThemeIcon variant="light" color={SEMANTIC.metrics.cancellations} size="lg" radius="md">
                <IconX size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Отмены / неявки
              </Text>
            </Group>
            <Text fw={700} fz="xl" c="gray.9">
              {(data?.bookings_cancelled ?? 0) + (data?.bookings_no_show ?? 0)}
            </Text>
            <Text size="xs" c="dimmed" mt="xs">
              отменено {data?.bookings_cancelled ?? 0} · неявки {data?.bookings_no_show ?? 0}
            </Text>
            <Text size="xs" c="dimmed" mt={2}>
              к вчера: —
            </Text>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Виджет «Выручка, спасённая ИИ за ночь» — только при включённом Revenue Hunter (Фаза 5) */}
      {revenueHunter && isRevenueHunterEnabled(revenueHunter) && (
        <Card
          padding="md"
          radius="md"
          shadow="none"
          withBorder
          bg="white"
          styles={{
            root: {
              borderColor: "var(--mantine-color-ai-3)",
              background:
                "linear-gradient(120deg, var(--mantine-color-ai-0) 0%, var(--mantine-color-white) 55%)",
            },
          }}
        >
          <Group gap="xs" mb={4} wrap="nowrap">
            <ThemeIcon variant="light" color={SEMANTIC.ai.accent} size="lg" radius="md">
              <IconRobot size={18} />
            </ThemeIcon>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              Выручка, спасённая ИИ{" "}
              {revenueHunter.period === "night"
                ? "за ночь"
                : revenueHunter.period === "day"
                  ? "за день"
                  : revenueHunter.period === "week"
                    ? "за неделю"
                    : "за ночь"}
            </Text>
          </Group>
          <Text fw={700} fz="xl" c="teal.8">
            {revenueHunter.amount} ₽
          </Text>
        </Card>
      )}

      {/* Левая колонка ~60%: Attention Feed; правая ~40%: таймлайн на сегодня */}
      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Text size="sm" fw={600} mb="xs" c="gray.9">
            Лента внимания
          </Text>
          {attentionLoading ? (
            <PageSkeleton variant="table" rows={3} />
          ) : attentionItems.length === 0 ? (
            <EmptyState
              title="Пока всё спокойно"
              description="Нет срочных событий для реакции. Новые элементы появятся из чатов, конфликтов и напоминаний."
              action={{
                label: "Открыть чат",
                onClick: () => window.location.assign(ROUTE_PATHS.admin.omniChat),
              }}
            />
          ) : (
            <ScrollArea h={400} type="scroll">
              <Stack gap="xs">
                {attentionItems.map((item) => (
                  <Card
                    key={`${item.kind}-${item.id}`}
                    withBorder
                    radius="md"
                    padding="sm"
                    bg="white"
                    styles={{ root: { borderColor: "var(--mantine-color-gray-3)" } }}
                  >
                    <Group justify="space-between" align="flex-start">
                      <Stack gap={4}>
                        <Text fw={600} size="sm" truncate>
                          {item.patient_full_name || item.patient_phone || item.title}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {item.description}
                        </Text>
                        <Group gap="xs">
                          <Badge size="xs" color={KIND_COLOR[item.kind] ?? "gray"}>
                            {KIND_LABEL[item.kind] ?? item.kind}
                          </Badge>
                          {item.due_at && (
                            <Text size="xs" c="dimmed">
                              Срок: {new Date(item.due_at).toLocaleString()}
                            </Text>
                          )}
                        </Group>
                      </Stack>
                      <Button
                        size="xs"
                        variant="light"
                        color="indigo"
                        component={Link}
                        to={
                          item.conversation_id
                            ? `${ROUTE_PATHS.admin.omniChat}?conversation=${item.conversation_id}`
                            : ROUTE_PATHS.admin.attention
                        }
                      >
                        Взять в работу
                      </Button>
                    </Group>
                  </Card>
                ))}
              </Stack>
            </ScrollArea>
          )}
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Text size="sm" fw={600} mb="xs" c="gray.9">
            Записи на сегодня
          </Text>
          {bookingsLoading ? (
            <PageSkeleton variant="table" rows={5} />
          ) : !todayBookings?.length ? (
            <EmptyState
              title="Нет записей на эту дату"
              description="Записи на сегодня появятся в календаре."
              action={{
                label: "Расписание",
                onClick: () => window.location.assign(ROUTE_PATHS.admin.schedule),
              }}
            />
          ) : (
            <ScrollArea h={400} type="scroll">
              <Stack gap="xs">
                {todayBookings
                  .filter((b) => b.status !== "cancelled")
                  .sort((a, b) => {
                    const tA = String(a.appointment_time).slice(0, 5);
                    const tB = String(b.appointment_time).slice(0, 5);
                    return tA.localeCompare(tB);
                  })
                  .slice(0, 20)
                  .map((b) => (
                    <Card
                      key={b.id}
                      withBorder
                      radius="md"
                      padding="sm"
                      style={{ cursor: "pointer", textDecoration: "none", color: "inherit" }}
                      onClick={() => setTimelineBooking(b)}
                    >
                      <Group justify="space-between">
                        <Text size="sm" fw={500}>
                          {String(b.appointment_time).slice(0, 5)}
                        </Text>
                        <Badge size="xs" variant="light">
                          {b.status}
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed">
                        Пациент: {b.patient_id}
                      </Text>
                      <Text size="xs" c="dimmed">
                        Врач: {b.doctor_id} · Услуга: {b.service_id}
                      </Text>
                    </Card>
                  ))}
              </Stack>
            </ScrollArea>
          )}
        </Grid.Col>
      </Grid>

      <AdminDrawer
        opened={timelineBooking !== null}
        onClose={() => setTimelineBooking(null)}
        position="right"
        size="md"
        title="Запись на сегодня"
      >
        {timelineBooking && (
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              Время
            </Text>
            <Text size="md">
              {String(timelineBooking.appointment_time).slice(0, 5)}
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
              Пациент
            </Text>
            <Text size="md">{timelineBooking.patient_id}</Text>
            <Text size="sm" c="dimmed" mt="xs">
              Врач · Услуга
            </Text>
            <Text size="md">
              {timelineBooking.doctor_id} · {timelineBooking.service_id}
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
              Статус
            </Text>
            <Badge size="sm" variant="light">
              {timelineBooking.status}
            </Badge>
            <Button
              component={Link}
              to={ROUTE_PATHS.admin.schedule}
              variant="light"
              mt="md"
              onClick={() => setTimelineBooking(null)}
            >
              Открыть в расписании
            </Button>
          </Stack>
        )}
      </AdminDrawer>
    </Stack>
  );
}
