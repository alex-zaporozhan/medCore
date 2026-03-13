import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAttentionFeed, useCloseFollowUp } from "@/hooks/useAttentionFeed";
import type { AttentionItem } from "@/api/types";
import {
  Badge,
  Button,
  Card,
  Flex,
  Grid,
  Group,
  ScrollArea,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useMemo } from "react";

function AttentionColumn({
  title,
  items,
  onCloseFollowUp,
}: {
  title: string;
  items: AttentionItem[];
  onCloseFollowUp?: (item: AttentionItem) => void;
}) {
  return (
    <Stack gap="sm">
      <Title order={5}>{title}</Title>
      <ScrollArea h={420} type="scroll">
        <Stack gap="xs">
          {items.length === 0 ? (
            <Text size="sm" c="dimmed">
              Нет элементов.
            </Text>
          ) : (
            items.map((item) => (
              <Card key={`${item.kind}-${item.id}`} withBorder radius="md" padding="sm">
                <Stack gap={4}>
                  <Group justify="space-between" align="center">
                    <Text fw={600} size="sm" truncate>
                      {item.patient_full_name || item.patient_phone || item.title}
                    </Text>
                    <Badge size="xs" color={item.kind === "conflict" ? "red" : item.kind === "follow_up" ? "blue" : "yellow"}>
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
                    <Group gap="xs">
                      <Badge size="xs" color="gray" variant="light">
                        Приоритет: {item.priority}
                      </Badge>
                      {item.assigned_admin_name && (
                        <Badge size="xs" variant="outline">
                          {item.assigned_admin_name}
                        </Badge>
                      )}
                      {item.has_comment && item.last_comment_preview && (
                        <Badge size="xs" variant="light" color="teal">
                          Есть комментарий
                        </Badge>
                      )}
                    </Group>
                    {item.kind === "follow_up" && item.status === "open" && onCloseFollowUp && (
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => onCloseFollowUp(item)}
                      >
                        Отметить выполненным
                      </Button>
                    )}
                  </Group>
                </Stack>
              </Card>
            ))
          )}
        </Stack>
      </ScrollArea>
    </Stack>
  );
}

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
        <Title order={3}>Лента внимания</Title>
        <Text size="sm" c="dimmed">
          Выберите клинику в шапке.
        </Text>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack>
        <Title order={3}>Лента внимания</Title>
        <Text size="sm" c="dimmed">
          Загрузка...
        </Text>
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <Title order={3}>Лента внимания</Title>
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

  return (
    <Stack gap="md">
      <Flex justify="space-between" align="center" wrap="wrap" gap="sm">
        <Title order={3}>Лента внимания</Title>
        <Button
          size="xs"
          variant="light"
          onClick={() => window.location.reload()}
        >
          Обновить
        </Button>
      </Flex>
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <AttentionColumn
            title="Обещали перезвонить"
            items={followUps}
            onCloseFollowUp={handleCloseFollowUp}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <AttentionColumn
            title="Давно не были"
            items={retentionGap}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <AttentionColumn
            title="Конфликты и жалобы"
            items={conflicts}
          />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

