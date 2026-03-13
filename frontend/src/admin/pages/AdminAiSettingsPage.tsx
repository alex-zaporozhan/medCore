import { useState, useEffect } from "react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { api } from "@/api/client";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
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

type AiMode = "draft_only" | "safe_autoreply" | "analytics_only";

interface AiSettings {
  ai_enabled: boolean;
  ai_mode: AiMode;
  ai_business_prompt: string | null;
  ai_allowed_intents: string[];
  ai_autoreply_enabled: boolean;
  ai_autoreply_hours: Record<string, unknown> | null;
  ai_provider_type: string;
}

interface AiStatusResponse {
  ai_mode: "disabled" | "fallback_local" | "external_active";
  features: Record<string, boolean>;
}

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

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<AiStatusResponse | null>(null);

  useEffect(() => {
    if (!clinicId) return;
    setLoading(true);
    setError(null);
    api
      .get<AiSettings>(`/v1/admin/clinics/${clinicId}/ai-settings`)
      .then((res) => {
        setSettings(res);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Ошибка загрузки настроек AI");
      })
      .finally(() => setLoading(false));

    setStatusLoading(true);
    api
      .get<AiStatusResponse>("/v1/admin/ai-status")
      .then((res) => {
        setAiStatus(res);
      })
      .catch(() => {
        // мягко игнорируем, статус не блокирует работу страницы
      })
      .finally(() => setStatusLoading(false));
  }, [clinicId]);

  const handleSave = () => {
    if (!clinicId || !settings) return;
    setSaving(true);
    setError(null);
    api
      .put<AiSettings>(`/v1/admin/clinics/${clinicId}/ai-settings`, settings)
      .then((res) => setSettings(res))
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Ошибка сохранения настроек AI");
      })
      .finally(() => setSaving(false));
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

  if (loading && !settings) {
    return (
      <Stack>
        <Title order={3}>AI и ассистент</Title>
        <DataSkeleton lines={4} />
      </Stack>
    );
  }

  if (error && !settings) {
    return (
      <Stack>
        <Title order={3}>AI и ассистент</Title>
        <Text c="red" size="sm">
          {error}
        </Text>
      </Stack>
    );
  }

  const s = settings!;

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
        </Stack>
      </Paper>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="sm">
          <Switch
            label="Включить AI‑ассистента"
            checked={s.ai_enabled}
            onChange={(e) =>
              setSettings((prev) => (prev ? { ...prev, ai_enabled: e.currentTarget.checked } : prev))
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
              setSettings((prev) => (prev ? { ...prev, ai_mode: (v as AiMode) ?? "draft_only" } : prev))
            }
          />
          <Textarea
            label="Контекст бизнеса и тон общения"
            description="Опишите кратко, чем вы занимаетесь, как обращаться к клиентам и чего нельзя обещать."
            minRows={4}
            value={s.ai_business_prompt ?? ""}
            onChange={(e) =>
              setSettings((prev) => (prev ? { ...prev, ai_business_prompt: e.currentTarget.value } : prev))
            }
          />
          <MultiSelect
            label="Где разрешён автоответ AI"
            description="Используется только в режиме безопасного автоответа."
            data={INTENT_OPTIONS}
            value={s.ai_allowed_intents ?? []}
            onChange={(vals) =>
              setSettings((prev) => (prev ? { ...prev, ai_allowed_intents: vals } : prev))
            }
          />
          <Checkbox
            label="Разрешить автоответ в разрешённых сценариях"
            checked={s.ai_autoreply_enabled}
            onChange={(e) =>
              setSettings((prev) =>
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
          {error && (
            <Text c="red" size="sm">
              {error}
            </Text>
          )}
          <Group justify="flex-end" mt="sm">
            <Button onClick={handleSave} loading={saving}>
              Сохранить настройки
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Stack>
  );
}

