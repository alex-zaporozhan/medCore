import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

interface ConflictItem {
  conversation_id: string;
  sentiment: string;
  issue_category: string;
  is_conflict: boolean;
  is_resolved: boolean;
  admin_mistakes: string[];
  business_root_causes: string[];
  suggested_playbook: string[];
  created_at: string;
}

interface ConflictSummary {
  total: number;
  unresolved_conflicts: number;
  top_issue_categories: string[];
}

interface ConflictReportResponse {
  summary: ConflictSummary;
  items: ConflictItem[];
  ai_status?: string | null;
}

function AdminAiReportsPage() {
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["admin-ai-reports-conflicts", dateFrom, dateTo],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      return api.get<ConflictReportResponse>(`/v1/admin/ai-reports/conflicts?${params.toString()}`);
    },
    enabled: !!dateFrom && !!dateTo,
  });

  const report = data;
  const items = report?.items ?? [];
  const summary = report?.summary;
  const aiStatus = report?.ai_status ?? null;

  const renderEmptyText = () => {
    if (aiStatus === "external_active") {
      return "За выбранный период конфликтов не найдено.";
    }
    if (aiStatus === "fallback_local" || aiStatus === "disabled") {
      return "AI‑анализ конфликтов сейчас недоступен. Вы можете продолжать работать с чатами и отчётами вручную.";
    }
    return "Данных по конфликтам за выбранный период нет.";
  };

  return (
    <Stack gap="md">
      <Title order={3}>AI‑отчёты по конфликтам</Title>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="sm">
          <Group gap="sm" wrap="wrap">
            <TextInput
              label="С даты"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.currentTarget.value)}
            />
            <TextInput
              label="По дату"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.currentTarget.value)}
            />
            <Button
              mt="auto"
              onClick={() => {
                if (dateFrom && dateTo) {
                  refetch();
                }
              }}
              disabled={!dateFrom || !dateTo}
              loading={isFetching}
            >
              Обновить отчёт
            </Button>
          </Group>

          {isLoading && !report && <DataSkeleton lines={4} />}

          {isError && !report && (
            <Text c="red">
              {error instanceof Error ? error.message : "Ошибка загрузки отчёта"}
            </Text>
          )}

          {summary && (
            <Paper p="sm" radius="md" withBorder>
              <Text fw={600} size="sm">
                Итоги за период
              </Text>
              <Text size="sm">
                Всего конфликтов: {summary.total}. Нерешённых: {summary.unresolved_conflicts}.
              </Text>
              {summary.top_issue_categories.length > 0 && (
                <Text size="sm">
                  Частые причины: {summary.top_issue_categories.join(", ")}.
                </Text>
              )}
            </Paper>
          )}

          {!isLoading && !isError && (!items.length || !report) && (
            <EmptyStateHint
              title="Нет данных для отчёта"
              subtitle={renderEmptyText()}
            />
          )}

          {!isLoading && !isError && items.length > 0 && (
            <Paper p="sm" radius="md" withBorder>
              <Table striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Дата</Table.Th>
                    <Table.Th>Категория</Table.Th>
                    <Table.Th>Тон</Table.Th>
                    <Table.Th>Конфликт</Table.Th>
                    <Table.Th>Статус</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((item) => (
                    <Table.Tr key={item.conversation_id + item.created_at}>
                      <Table.Td>{new Date(item.created_at).toLocaleString()}</Table.Td>
                      <Table.Td>{item.issue_category}</Table.Td>
                      <Table.Td>{item.sentiment}</Table.Td>
                      <Table.Td>{item.is_conflict ? "Да" : "Нет"}</Table.Td>
                      <Table.Td>{item.is_resolved ? "Закрыт" : "Открыт"}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

export default AdminAiReportsPage;

