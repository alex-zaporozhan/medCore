import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAdminIntegrationSettings1c,
  useUpdateAdminIntegrationSettings1cMutation,
} from "@/hooks/useAdminIntegrations";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Alert, Button, Stack, TextInput } from "@mantine/core";
import { AdminSettingsSectionCard, ContextBar } from "@/shared/ui";
import { useState, useEffect } from "react";

export default function AdminIntegrationsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? "";

  const { data: settings1c } = useAdminIntegrationSettings1c(clinicId);
  const [url1c, setUrl1c] = useState(settings1c?.api_url ?? "");
  const [key1c, setKey1c] = useState("");
  const [saving1c, setSaving1c] = useState(false);

  useEffect(() => {
    setUrl1c(settings1c?.api_url ?? "");
  }, [settings1c?.api_url]);

  const save1c = useUpdateAdminIntegrationSettings1cMutation(clinicId);

  const handleSave1c = () => {
    setSaving1c(true);
    save1c.mutate(
      { api_url: url1c.trim() || null, credentials: key1c.trim() || null },
      {
        onSuccess: () => setKey1c(""),
        onSettled: () => setSaving1c(false),
      }
    );
  };

  if (!currentClinicId) {
    return (
      <Stack>
        <ContextBar title="Интеграции" />
        <EmptyStateHint title="Выберите клинику" />
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Интеграции" />
      <Alert color="blue" title="CSV-обмен">
        Импорт расписания и экспорт закрытых записей в CSV доступны в разделе «Расписание» и в отчётах. Выгрузка подходит для загрузки в 1C.
      </Alert>

      <AdminSettingsSectionCard
        title="1C"
        description="URL и ключ API для будущей синхронизации с 1C. Настройки сохраняются в зашифрованном виде."
      >
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
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="Bitrix24"
        description="Подключение по API планируется в следующих версиях. Сейчас доступны CSV и интеграция 1C."
      />
    </Stack>
  );
}
