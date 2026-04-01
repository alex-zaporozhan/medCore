import { useState } from "react";
import { useAdminAiConflictReport } from "@/hooks/useAdminAiReports";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { QueryErrorAlert, ContextBar, AdminDataTableToolbar, ADMIN_TABLE_PROPS } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";

function AdminAiReportsPage() {
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  const { data, isLoading, isError, error, refetch, isFetching } = useAdminAiConflictReport(
    dateFrom,
    dateTo
  );

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
    <Stack gap="md" className="admin-form-stack">
      <ContextBar title="AI‑отчёты по конфликтам" />
      <AdminDataTableToolbar>
        <Group gap="sm" wrap="wrap" align="flex-end">
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
      </AdminDataTableToolbar>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="sm">
          {isLoading && !report && <DataSkeleton lines={4} />}

          {isError && !report && <QueryErrorAlert error={error} title="Не удалось загрузить отчёт" />}

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
            <Paper p="sm" radius="md" withBorder className="data-table-card">
              <Table striped {...ADMIN_TABLE_PROPS}>
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

