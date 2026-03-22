import { useState, useEffect } from "react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAdminClinicAiSettings,
  useAdminAiStatus,
  useUpdateAdminClinicAiSettingsMutation,
  type AdminClinicAiSettings,
  type AiMode,
} from "@/hooks";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { QueryErrorAlert } from "@/shared/ui";
import {
  Button,
  Checkbox,
  Group,
  MultiSelect,
  Paper,
  Stack,
  Switch,
  Text,
  Textarea,
  Title,
  Select,
} from "@mantine/core";

const INTENT_OPTIONS = [
  { value: "schedule", label: "Расписание" },
  { value: "location", label: "Адрес / как добраться" },
  { value: "faq", label: "FAQ" },
  { value: "booking_change", label: "Перенос/изменение записи" },
  { value: "price_info", label: "Информация о цене" },
];

export default function AdminAiSettingsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  const {
    data: settingsData,
    isLoading,
    isError,
    error: loadError,
  } = useAdminClinicAiSettings(clinicId);
  const {
    data: aiStatus,
    isLoading: statusLoading,
    isError: statusError,
  } = useAdminAiStatus();
  const updateMutation = useUpdateAdminClinicAiSettingsMutation(clinicId);

  const [draft, setDraft] = useState<AdminClinicAiSettings | null>(null);

  useEffect(() => {
    if (settingsData) setDraft(settingsData);
  }, [settingsData]);

  const handleSave = () => {
    if (!draft || !clinicId) return;
    updateMutation.mutate(draft);
  };

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>AI и ассистент</Title>
        <Text c="dimmed" size="sm">
          Сначала выберите клинику в шапке.
        </Text>
      </Stack>
    );
  }

  if (isLoading && !draft) {
    return (
      <Stack>
        <Title order={3}>AI и ассистент</Title>
        <DataSkeleton lines={4} />
      </Stack>
    );
  }

  if (isError && !draft) {
    return (
      <Stack>
        <Title order={3}>AI и ассистент</Title>
        <QueryErrorAlert error={loadError} title="Не удалось загрузить настройки AI" />
      </Stack>
    );
  }

  const s = draft;
  if (!s) {
    return (
      <Stack>
        <Title order={3}>AI и ассистент</Title>
        <DataSkeleton lines={4} />
      </Stack>
    );
  }

  return (
    <Stack>
      <Title order={3}>AI и ассистент</Title>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="xs">
          {statusLoading && <DataSkeleton lines={1} />}
          {aiStatus && !statusLoading && (
            <Stack gap={4}>
              <Text fw={500}>
                {aiStatus.ai_mode === "external_active"
                  ? "AI подключён (внешний провайдер активен)."
                  : aiStatus.ai_mode === "fallback_local"
                    ? "AI в локальном режиме (подсказки без внешнего провайдера)."
                    : "AI отключён."}
              </Text>
              <Text size="xs" c="dimmed">
                В режиме внешнего AI доступны подробные резюме диалогов, подсказки ответов, обзоры по пациентам и
                отчёты по конфликтам. В локальном режиме используются упрощённые подсказки без обращения к внешнему
                провайдеру.
              </Text>
            </Stack>
          )}
          {statusError && !statusLoading && !aiStatus && (
            <Text size="xs" c="dimmed">
              Статус AI недоступен (сервер или сеть). Настройки клиники ниже можно редактировать.
            </Text>
          )}
        </Stack>
      </Paper>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="sm">
          <Switch
            label="Включить AI‑ассистента"
            checked={s.ai_enabled}
            onChange={(e) =>
              setDraft((prev) => (prev ? { ...prev, ai_enabled: e.currentTarget.checked } : prev))
            }
          />
          <Select
            label="Режим AI"
            description="Черновики, безопасный автоответ или только аналитика"
            data={[
              { value: "draft_only", label: "Только черновики" },
              { value: "safe_autoreply", label: "Безопасный автоответ" },
              { value: "analytics_only", label: "Только аналитика" },
            ]}
            value={s.ai_mode}
            onChange={(v) =>
              setDraft((prev) => (prev ? { ...prev, ai_mode: (v as AiMode) ?? "draft_only" } : prev))
            }
          />
          <Textarea
            label="Контекст бизнеса и тон общения"
            description="Опишите кратко, чем вы занимаетесь, как обращаться к клиентам и чего нельзя обещать."
            minRows={4}
            value={s.ai_business_prompt ?? ""}
            onChange={(e) =>
              setDraft((prev) => (prev ? { ...prev, ai_business_prompt: e.currentTarget.value } : prev))
            }
          />
          <MultiSelect
            label="Где разрешён автоответ AI"
            description="Используется только в режиме безопасного автоответа."
            data={INTENT_OPTIONS}
            value={s.ai_allowed_intents ?? []}
            onChange={(vals) =>
              setDraft((prev) => (prev ? { ...prev, ai_allowed_intents: vals } : prev))
            }
          />
          <Checkbox
            label="Разрешить автоответ в разрешённых сценариях"
            checked={s.ai_autoreply_enabled}
            onChange={(e) =>
              setDraft((prev) =>
                prev ? { ...prev, ai_autoreply_enabled: e.currentTarget.checked } : prev,
              )
            }
          />
          <Text size="xs" c="dimmed">
            Детальная настройка расписания автоответа (часы/дни) будет добавлена позже. Сейчас AI
            опирается только на выбранные типы сценариев.
          </Text>
          <Text size="sm">
            Текущий тип провайдера: <b>{s.ai_provider_type}</b>
          </Text>
          {updateMutation.isError && (
            <QueryErrorAlert error={updateMutation.error} title="Не удалось сохранить настройки AI" />
          )}
          <Group justify="flex-end" mt="sm">
            <Button color="ai" onClick={handleSave} loading={updateMutation.isPending}>
              Сохранить настройки
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Stack>
  );
}
