import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAttentionFeed,
  useCloseFollowUp,
  useCreateAttentionFeedTask,
} from "@/hooks/useAttentionFeed";
import type { AttentionItem } from "@/api/types";
import {
  Badge,
  Button,
  Card,
  Grid,
  Group,
  ScrollArea,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { useMemo } from "react";
import { ROUTE_PATHS } from "@/routePaths";

export default function AdminAttentionFeedPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const { data, isLoading, isError, error } = useAttentionFeed(clinicId);
  const closeMutation = useCloseFollowUp(clinicId);
  const createTaskMutation = useCreateAttentionFeedTask(clinicId);

  const followUps = useMemo(() => data?.follow_up ?? [], [data]);
  const retentionGap = useMemo(() => data?.retention_gap ?? [], [data]);
  const conflicts = useMemo(() => data?.conflicts ?? [], [data]);

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Лента внимания" />
        <Text size="sm" c="dimmed">
          Выберите клинику в шапке.
        </Text>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Лента внимания" />
        <PageSkeleton variant="table" rows={6} />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <ContextBar title="Лента внимания" />
        <QueryErrorAlert error={error} title="Не удалось загрузить ленту внимания" />
      </Stack>
    );
  }

  const handleCloseFollowUp = (item: AttentionItem) => {
    if (!clinicId) return;
    closeMutation.mutate(item.id);
  };

  const allFeedItems = useMemo(
    () =>
      [
        ...followUps.map((i) => ({ ...i, kind: "follow_up" as const })),
        ...retentionGap.map((i) => ({ ...i, kind: "retention_gap" as const })),
        ...conflicts.map((i) => ({ ...i, kind: "conflict" as const })),
      ].sort((a, b) => a.priority - b.priority),
    [followUps, retentionGap, conflicts]
  );

  return (
    <Stack gap="md">
      <ContextBar
        title="Лента внимания"
        actions={
          <Button size="sm" variant="light" onClick={() => window.location.reload()}>
            Обновить
          </Button>
        }
      />
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Title order={5} mb="xs">
            Attention Feed
          </Title>
          {allFeedItems.length === 0 ? (
            <EmptyState
              title="Пока всё спокойно"
              description="Нет срочных событий для реакции."
              action={{
                label: "Открыть чат",
                onClick: () => window.location.assign(ROUTE_PATHS.admin.omniChat),
              }}
            />
          ) : (
            <ScrollArea h={500} type="scroll">
              <Stack gap="xs">
                {allFeedItems.map((item) => (
                  <Card key={`${item.kind}-${item.id}`} withBorder radius="md" padding="sm">
                    <Stack gap={4}>
                      <Group justify="space-between" align="center">
                        <Text fw={600} size="sm" truncate>
                          {item.patient_full_name || item.patient_phone || item.title}
                        </Text>
                        <Badge
                          size="xs"
                          color={
                            item.kind === "conflict"
                              ? "red"
                              : item.kind === "follow_up"
                                ? "blue"
                                : "yellow"
                          }
                        >
                          {item.kind === "follow_up"
                            ? "Перезвонить"
                            : item.kind === "retention_gap"
                              ? "Давно не был"
                              : "Конфликт"}
                        </Badge>
                        <Badge
                          size="xs"
                          variant="outline"
                          color={
                            item.status === "resolved"
                              ? "green"
                              : item.status === "in_progress"
                                ? "blue"
                                : item.status === "archived"
                                  ? "gray"
                                  : "yellow"
                          }
                        >
                          {item.status}
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed">
                        {item.description}
                      </Text>
                      {item.due_at && (
                        <Text size="xs" c="dimmed">
                          Срок: {new Date(item.due_at).toLocaleString()}
                        </Text>
                      )}
                      <Group gap="xs" justify="space-between" align="center" mt={4}>
                        <Group gap="xs">
                          {item.tasks_total > 0 && (
                            <Text size="xs" c="dimmed">
                              Задач: {item.tasks_total} (в работе: {item.tasks_open + item.tasks_in_progress})
                            </Text>
                          )}
                        </Group>
                        <Group gap="xs">
                          {item.kind === "follow_up" && item.status === "new" && (
                            <Button size="xs" variant="light" onClick={() => handleCloseFollowUp(item)}>
                              Взять в работу
                            </Button>
                          )}
                          {clinicId && (
                            <Button
                              size="xs"
                              variant="subtle"
                              loading={createTaskMutation.isPending}
                              onClick={() =>
                                createTaskMutation.mutate({
                                  kind: item.kind,
                                  id: item.id,
                                  title: item.title,
                                  description: item.description,
                                })
                              }
                            >
                              Создать задачу
                            </Button>
                          )}
                        </Group>
                      </Group>
                    </Stack>
                  </Card>
                ))}
              </Stack>
            </ScrollArea>
          )}
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Title order={5} mb="xs">
            My Focus
          </Title>
          <EmptyState
            title="Личные задачи"
            description="Задачи, взятые в работу, появятся здесь. Управление задачами — в разделе «Задачи»."
            action={{
              label: "Открыть задачи",
              onClick: () => window.location.assign(ROUTE_PATHS.admin.tasks),
            }}
          />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

