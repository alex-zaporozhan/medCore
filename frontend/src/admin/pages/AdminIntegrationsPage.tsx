import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Alert, Button, Card, Stack, Text, TextInput, Title } from "@mantine/core";
import { useState, useEffect } from "react";

interface IntegrationSettings {
  provider: string;
  api_url: string | null;
  has_credentials: boolean;
}

export default function AdminIntegrationsPage() {
  const { currentClinicId } = useAdminClinic();
  const qc = useQueryClient();
  const clinicId = currentClinicId ?? "";

  const { data: settings1c } = useQuery({
    queryKey: ["integration-settings", clinicId, "1c"],
    queryFn: () => api.get<IntegrationSettings>(`/v1/admin/clinics/${clinicId}/integration-settings/1c`),
    enabled: !!clinicId,
  });
  const [url1c, setUrl1c] = useState(settings1c?.api_url ?? "");
  const [key1c, setKey1c] = useState("");
  const [saving1c, setSaving1c] = useState(false);

  useEffect(() => {
    setUrl1c(settings1c?.api_url ?? "");
  }, [settings1c?.api_url]);

  const save1c = useMutation({
    mutationFn: (body: { api_url?: string | null; credentials?: string | null }) =>
      api.put<IntegrationSettings>(`/v1/admin/clinics/${clinicId}/integration-settings/1c`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["integration-settings", clinicId, "1c"] });
      setKey1c("");
    },
  });

  const handleSave1c = () => {
    setSaving1c(true);
    save1c.mutate(
      { api_url: url1c.trim() || null, credentials: key1c.trim() || null },
      { onSettled: () => setSaving1c(false) }
    );
  };

  if (!currentClinicId) {
    return (
      <Stack>
        <Title order={3}>Интеграции</Title>
        <EmptyStateHint title="Выберите клинику" />
      </Stack>
    );
  }

  return (
    <Stack>
      <Title order={3}>Интеграции</Title>
      <Alert color="blue" title="CSV-обмен">
        Импорт расписания и экспорт закрытых записей в CSV доступны в разделе «Расписание» и в отчётах. Выгрузка подходит для загрузки в 1C.
      </Alert>

      <Card withBorder p="md" radius="md">
        <Stack gap="md">
          <Text fw={600} size="sm">1C</Text>
          <Text size="xs" c="dimmed">
            URL и ключ API для будущей синхронизации с 1C. Настройки сохраняются в зашифрованном виде.
          </Text>
          <TextInput
            label="URL API 1C"
            placeholder="https://..."
            value={url1c}
            onChange={(e) => setUrl1c(e.currentTarget.value)}
          />
          <TextInput
            type="password"
            label="Ключ / логин (API)"
            placeholder="Оставьте пустым, чтобы не менять сохранённый ключ"
            value={key1c}
            onChange={(e) => setKey1c(e.currentTarget.value)}
          />
          <Button onClick={handleSave1c} loading={saving1c}>
            Сохранить настройки 1C
          </Button>
        </Stack>
      </Card>

      <Card withBorder p="md" radius="md">
        <Stack gap="md">
          <Text fw={600} size="sm">Bitrix24</Text>
          <Text size="xs" c="dimmed">
            Подключение по API планируется в следующих версиях. Сейчас доступны CSV и интеграция 1C.
          </Text>
        </Stack>
      </Card>
    </Stack>
  );
}
