import { useReportsDashboard } from "@/hooks/useReports";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Card, Grid, Stack, Text, Title } from "@mantine/core";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";

const EMPTY_DB_HINT =
  "Если ошибка из-за отсутствия данных в базе — добавьте клинику, врачей или пациентов в соответствующих разделах.";
const BACKEND_HINT =
  "Если данные не загружаются, проверьте, что бэкенд запущен на порту 8000 (см. docs/RUN_SERVICES.md).";

export default function AdminDashboardPage() {
  useAdminClinic();
  const date = dayjs().format("YYYY-MM-DD");
  const { data, isLoading, isError, error } = useReportsDashboard(date, "day");

  if (isLoading) {
    return (
      <Stack>
        <Title order={3}>Дашборд</Title>
        <Text size="sm" c="dimmed">{BACKEND_HINT}</Text>
        <DataSkeleton lines={4} />
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}><DataSkeleton card /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><DataSkeleton card /></Grid.Col>
        </Grid>
      </Stack>
    );
  }

  if (isError) {
    const message = error instanceof Error ? error.message : "Ошибка загрузки";
    const isEmptyDb =
      message.includes("клиник") || message.includes("клиники");
    const isNetwork = message.includes("Failed") || message.includes("сеть") || message.includes("network");
    return (
      <Stack>
        <Title order={3}>Дашборд</Title>
        <Text c="red">{message}</Text>
        {isEmptyDb && (
          <Text size="sm" c="dimmed">
            {EMPTY_DB_HINT}
          </Text>
        )}
        {isNetwork && (
          <Text size="sm" c="dimmed">
            {BACKEND_HINT}
          </Text>
        )}
      </Stack>
    );
  }

  if (!data) {
    return (
      <Stack>
        <Title order={3}>Дашборд</Title>
        <EmptyStateHint title="Нет данных за выбранную дату" />
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Title order={3}>Дашборд</Title>
      <Text c="dimmed">Сводка за {dayjs(data.date).format("DD.MM.YYYY")}</Text>

      {/* Крупные метрики сверху */}
      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card
            padding="lg"
            radius="md"
            shadow="sm"
            style={{
              background: `linear-gradient(135deg, var(--primary), var(--primary-active))`,
              color: "var(--text-on-primary)",
            }}
          >
            <Text size="sm" style={{ color: "var(--text-on-primary)", opacity: 0.9 }}>
              Записей сегодня
            </Text>
            <Text fw={700} style={{ fontSize: 32, lineHeight: 1.1 }}>
              {data.bookings_pending +
                data.bookings_confirmed +
                data.bookings_completed}
            </Text>
            <Text size="sm" style={{ color: "var(--text-on-primary)", opacity: 0.9 }} mt="sm">
              Ожидают: {data.bookings_pending}, подтверждено:{" "}
              {data.bookings_confirmed}, оказано: {data.bookings_completed}
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card padding="lg" radius="md" shadow="sm">
            <Text size="sm" c="dimmed">
              Выручка за день
            </Text>
            <Text fw={700} style={{ fontSize: 32, lineHeight: 1.1 }}>
              {data.revenue} ₽
            </Text>
            <Text size="sm" c="dimmed" mt="sm">
              Включает подтверждённые онлайн‑платежи и предоплаты по записям.
            </Text>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Детализация по статусам и пациентам */}
      <Grid>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Text size="sm" c="dimmed">
              Ожидают
            </Text>
            <Text fw={700} fz="xl">
              {data.bookings_pending}
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Text size="sm" c="dimmed">
              Подтверждено
            </Text>
            <Text fw={700} fz="xl">
              {data.bookings_confirmed}
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Text size="sm" c="dimmed">
              Оказано
            </Text>
            <Text fw={700} fz="xl">
              {data.bookings_completed}
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Text size="sm" c="dimmed">
              Отменено
            </Text>
            <Text fw={700} fz="xl">
              {data.bookings_cancelled}
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Text size="sm" c="dimmed">
              Неявки
            </Text>
            <Text fw={700} fz="xl">
              {data.bookings_no_show}
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card shadow="sm" padding="md" radius="md" withBorder>
            <Text size="sm" c="dimmed">
              Новые пациенты
            </Text>
            <Text fw={700} fz="xl">
              {data.new_patients}
            </Text>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
