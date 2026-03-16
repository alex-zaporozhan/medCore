import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAttentionFeed, useCloseFollowUp } from "@/hooks/useAttentionFeed";
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
import { useMemo } from "react";

export default function AdminAttentionFeedPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const { data, isLoading, isError, error } = useAttentionFeed(clinicId);
  const closeMutation = useCloseFollowUp(clinicId);

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
        <Text size="sm" c="dimmed">
          Загрузка...
        </Text>
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <ContextBar title="Лента внимания" />
        <Text size="sm" c="red">
          {error instanceof Error ? error.message : "Ошибка загрузки ленты внимания"}
        </Text>
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
                onClick: () => window.location.assign("/admin/omni-chat"),
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
                        {item.kind === "follow_up" && item.status === "open" && (
                          <Button size="xs" variant="light" onClick={() => handleCloseFollowUp(item)}>
                            Взять в работу
                          </Button>
                        )}
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
              onClick: () => window.location.assign("/admin/tasks"),
            }}
          />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

