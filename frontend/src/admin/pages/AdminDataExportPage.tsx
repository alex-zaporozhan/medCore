import { API_BASE, getAdminToken } from "@/api/client";
import {
  useAdminDataExportSummary,
  useRequestDataExportMutation,
} from "@/hooks/useAdminDataExport";
import { useAdminSession } from "@/hooks/useAdminSession";
import { AdminSettingsSectionCard, ContextBar } from "@/shared/ui";
import { Alert, Button, Code, Group, List, Stack, Text, Textarea } from "@mantine/core";
import { useState } from "react";

export default function AdminDataExportPage() {
  const { data: session } = useAdminSession();
  const isOwner = session?.roles?.includes("owner") ?? false;
  const orgReady = Boolean(session?.organization_id);
  const summaryQ = useAdminDataExportSummary(isOwner && orgReady);
  const requestMut = useRequestDataExportMutation();
  const [note, setNote] = useState("");

  const downloadManifest = async () => {
    const token = getAdminToken();
    const res = await fetch(`${API_BASE}/v1/admin/organization/data-export/manifest.jsonl`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      window.alert(`Ошибка загрузки: ${res.status}`);
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "export_manifest.jsonl";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOwner) {
    return (
      <Stack p="md">
        <ContextBar title="Экспорт данных" />
        <Alert color="yellow">Раздел доступен только роли владельца организации.</Alert>
      </Stack>
    );
  }

  return (
    <Stack p="md">
      <ContextBar title="Экспорт данных и offboarding" />
      {!orgReady ? (
        <Alert color="gray">Привяжите организацию к администратору, чтобы увидеть сводку.</Alert>
      ) : (
        <>
          <AdminSettingsSectionCard title="Сводка (без PII)">
            {summaryQ.isLoading ? (
              <Text size="sm" c="dimmed">
                Загрузка…
              </Text>
            ) : summaryQ.error ? (
              <Alert color="red">Не удалось загрузить сводку</Alert>
            ) : (
              <Stack gap="xs">
                <Text size="sm">
                  Организация: <Code>{summaryQ.data?.organization_id}</Code>
                </Text>
                <Text size="sm" fw={600}>
                  Примерные объёмы
                </Text>
                <List size="sm" spacing="xs">
                  {Object.entries(summaryQ.data?.approximate_counts ?? {}).map(([k, v]) => (
                    <List.Item key={k}>
                      {k}: <strong>{v}</strong>
                    </List.Item>
                  ))}
                </List>
                <Text size="xs" c="dimmed">
                  {summaryQ.data?.formats_note}
                </Text>
              </Stack>
            )}
          </AdminSettingsSectionCard>

          <AdminSettingsSectionCard title="Machine-readable манифест (без персональных данных)">
            <Group>
              <Button variant="light" onClick={() => void downloadManifest()}>
                Скачать manifest.jsonl
              </Button>
            </Group>
            <Text size="xs" c="dimmed" mt="xs">
              JSON Lines: организация и клиники; для полной выгрузки PII — заявка ниже и OPS по регламенту.
            </Text>
          </AdminSettingsSectionCard>

          <AdminSettingsSectionCard title="Заявка на полную выгрузку">
            <Stack gap="sm">
              <Textarea
                label="Комментарий для OPS (необязательно)"
                minRows={2}
                value={note}
                onChange={(e) => setNote(e.currentTarget.value)}
                maxLength={500}
              />
              <Button
                loading={requestMut.isPending}
                onClick={() =>
                  requestMut.mutate(
                    { note: note.trim() || null },
                    {
                      onSuccess: (data) => window.alert(data.message),
                      onError: () => window.alert("Не удалось создать заявку"),
                    }
                  )
                }
              >
                Зарегистрировать заявку
              </Button>
            </Stack>
          </AdminSettingsSectionCard>
        </>
      )}
    </Stack>
  );
}
