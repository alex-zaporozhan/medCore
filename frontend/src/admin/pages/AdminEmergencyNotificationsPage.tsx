/**
 * Экстренные уведомления (бывш. «лента внимания»): только сюда, не на главной ленте.
 */
import { useAttentionFeed } from "@/hooks/useAttentionFeed";
import { PageSkeleton, EmptyState, ContextBar, QueryErrorAlert } from "@/shared/ui";
import {
  Badge,
  Button,
  Card,
  Group,
  ScrollArea,
  Stack,
  Text,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { useMemo } from "react";
import { ROUTE_PATHS } from "@/routePaths";
import type { AttentionItem } from "@/api/types";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { SEMANTIC } from "@/shared/semanticUi";

function flattenAttentionFeed(
  data:
    | { follow_up: AttentionItem[]; retention_gap: AttentionItem[]; conflicts: AttentionItem[] }
    | undefined
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
  follow_up: SEMANTIC.opsSeverity.info,
  retention_gap: SEMANTIC.opsSeverity.warning,
  conflict: SEMANTIC.opsSeverity.critical,
};

export default function AdminEmergencyNotificationsPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: attentionData, isLoading, isError, error } = useAttentionFeed(currentClinicId ?? null);
  const attentionItems = useMemo(() => flattenAttentionFeed(attentionData), [attentionData]);

  if (isLoading) {
    return (
      <Stack gap="md">
        <ContextBar title="Приоритетные сообщения" />
        <PageSkeleton variant="table" rows={4} />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack gap="md">
        <ContextBar title="Приоритетные сообщения" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <ContextBar title="Приоритетные сообщения" />
      <Text size="sm" c="dimmed">
        Приоритетные сообщения (отмена совещания, перенос пациентов при болезни врача и т.п.) — отдельно от главной ленты
        новостей. Дальше этот канал будет связан с системой персональных оповещений администратора.
      </Text>
      {attentionItems.length === 0 ? (
        <EmptyState
          title="Нет экстренных элементов"
          description="Когда появятся события из CRM, конфликтов слотов или напоминаний, они отобразятся здесь."
          action={{
            label: "На ленту",
            onClick: () => {
              window.location.assign(ROUTE_PATHS.admin.dashboard);
            },
          }}
        />
      ) : (
        <ScrollArea h={560} type="scroll">
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
                        : ROUTE_PATHS.admin.dashboard
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
    </Stack>
  );
}
