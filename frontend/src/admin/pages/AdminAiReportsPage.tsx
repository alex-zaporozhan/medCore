import { useState } from "react";
import { useTranslation } from "react-i18next";
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
  const { t, i18n } = useTranslation("reports");
  const listLocale = i18n.language.toLowerCase().startsWith("ru") ? "ru-RU" : "en-US";
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
      return t("aiEmptyExternal");
    }
    if (aiStatus === "fallback_local" || aiStatus === "disabled") {
      return t("aiEmptyFallback");
    }
    return t("aiEmptyGeneric");
  };

  return (
    <Stack gap="md" className="admin-form-stack">
      <ContextBar title={t("aiTitle")} />
      <AdminDataTableToolbar>
        <Group gap="sm" wrap="wrap" align="flex-end">
          <TextInput
            label={t("aiDateFrom")}
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.currentTarget.value)}
          />
          <TextInput
            label={t("aiDateTo")}
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
            {t("aiRefresh")}
          </Button>
        </Group>
      </AdminDataTableToolbar>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="sm">
          {isLoading && !report && <DataSkeleton lines={4} />}

          {isError && !report && <QueryErrorAlert error={error} title={t("aiLoadFailed")} />}

          {summary && (
            <Paper p="sm" radius="md" withBorder>
              <Text fw={600} size="sm">
              {t("aiSummary")}
              </Text>
              <Text size="sm">
                {t("aiSummaryCounts", {
                  total: summary.total,
                  unresolved: summary.unresolved_conflicts,
                })}
              </Text>
              {summary.top_issue_categories.length > 0 && (
                <Text size="sm">
                  {t("aiTopReasons", { list: summary.top_issue_categories.join(", ") })}
                </Text>
              )}
            </Paper>
          )}

          {(!dateFrom || !dateTo) && (
            <Text size="sm" c="dimmed">
              {t("aiPickDates")}
            </Text>
          )}

          {!isLoading && !isError && dateFrom && dateTo && (!items.length || !report) && (
            <EmptyStateHint
              title={t("aiEmptyTitle")}
              subtitle={renderEmptyText()}
            />
          )}

          {!isLoading && !isError && items.length > 0 && (
            <Paper p="sm" radius="md" withBorder className="data-table-card">
              <Table striped {...ADMIN_TABLE_PROPS}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("colDate")}</Table.Th>
                    <Table.Th>{t("colCategory")}</Table.Th>
                    <Table.Th>{t("colTone")}</Table.Th>
                    <Table.Th>{t("colConflict")}</Table.Th>
                    <Table.Th>{t("colStatus")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((item) => (
                    <Table.Tr key={item.conversation_id + item.created_at}>
                      <Table.Td>{new Date(item.created_at).toLocaleString(listLocale)}</Table.Td>
                      <Table.Td>{item.issue_category}</Table.Td>
                      <Table.Td>{item.sentiment}</Table.Td>
                      <Table.Td>{item.is_conflict ? t("yes") : t("no")}</Table.Td>
                      <Table.Td>{item.is_resolved ? t("closed") : t("open")}</Table.Td>
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

