import { useState, useEffect } from "react";
import {
  useOwnerOmniAiSettings,
  useUpdateOwnerOmniAiSettings,
  OMNI_AI_MODES,
  type OmniChannelAiSettings,
} from "@/hooks/useOwnerOmniAiSettings";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import {
  Box,
  Button,
  Paper,
  Select,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";

const AI_MODE_LABELS: Record<string, string> = {
  DISABLED: "Выключен",
  AUTO_REPLY: "Автоответ",
  SUGGEST_ONLY: "Только подсказки",
};

export default function AdminOmniAiSettingsPage() {
  const { data, isLoading, isError, error } = useOwnerOmniAiSettings();
  const updateMutation = useUpdateOwnerOmniAiSettings();

  const [businessMode, setBusinessMode] = useState<string>("DISABLED");
  const [channelModes, setChannelModes] = useState<Record<string, string>>({});

  useEffect(() => {
    if (data?.business) {
      setBusinessMode(data.business.ai_mode || "DISABLED");
    }
  }, [data?.business]);

  useEffect(() => {
    if (data?.channels) {
      const next: Record<string, string> = {};
      data.channels.forEach((ch) => {
        next[ch.channel_id] = ch.ai_mode || "DISABLED";
      });
      setChannelModes(next);
    }
  }, [data?.channels]);

  const handleSaveBusiness = () => {
    updateMutation.mutate({
      business: { ai_mode: businessMode },
    });
  };

  const handleChannelModeChange = (channelId: string, ai_mode: string) => {
    setChannelModes((prev) => ({ ...prev, [channelId]: ai_mode }));
  };

  const handleSaveChannels = () => {
    const channels = (data?.channels ?? []).map((ch) => ({
      channel_id: ch.channel_id,
      ai_mode: channelModes[ch.channel_id] ?? ch.ai_mode,
    }));
    if (channels.length === 0) return;
    updateMutation.mutate({ channels });
  };

  const hasChannelChanges =
    data?.channels?.some(
      (ch) => (channelModes[ch.channel_id] ?? ch.ai_mode) !== ch.ai_mode
    ) ?? false;

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="AI омниканального ассистента" />
        <DataSkeleton lines={5} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <ContextBar title="AI омниканального ассистента" />
        <Text c="red">{error instanceof Error ? error.message : "Ошибка загрузки"}</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <ContextBar title="AI омниканального ассистента" />
      <Text size="sm" c="dimmed">
        Глобальные настройки и переопределения по каналам (Telegram, веб-чат и др.).
      </Text>

      <Paper p="md" radius="md" withBorder>
        <Text fw={600} mb="xs">
          Режим по умолчанию (для всей клиники)
        </Text>
        <Box style={{ maxWidth: 320 }}>
          <Select
            label="Режим AI"
            data={OMNI_AI_MODES.map((v) => ({
              value: v,
              label: AI_MODE_LABELS[v] ?? v,
            }))}
            value={businessMode}
            onChange={(v) => v && setBusinessMode(v)}
          />
          <Button
            mt="sm"
            onClick={handleSaveBusiness}
            loading={updateMutation.isPending}
          >
            Сохранить
          </Button>
        </Box>
      </Paper>

      <Paper p="md" radius="md" withBorder>
        <Text fw={600} mb="xs">
          По каналам
        </Text>
        {!data?.channels?.length ? (
          <Text size="sm" c="dimmed">
            Нет настроенных каналов. Добавьте каналы в разделе «Единый чат» / Омниканальные каналы.
          </Text>
        ) : (
          <>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Канал</Table.Th>
                  <Table.Th>Тип</Table.Th>
                  <Table.Th>Режим AI</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.channels.map((ch: OmniChannelAiSettings) => (
                  <Table.Tr key={ch.channel_id}>
                    <Table.Td>{ch.channel_display_name}</Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {ch.channel_type}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Select
                        size="xs"
                        style={{ maxWidth: 180 }}
                        data={OMNI_AI_MODES.map((v) => ({
                          value: v,
                          label: AI_MODE_LABELS[v] ?? v,
                        }))}
                        value={channelModes[ch.channel_id] ?? ch.ai_mode}
                        onChange={(v) =>
                          v && handleChannelModeChange(ch.channel_id, v)
                        }
                      />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {hasChannelChanges && (
              <Button
                mt="sm"
                variant="light"
                onClick={handleSaveChannels}
                loading={updateMutation.isPending}
              >
                Сохранить изменения по каналам
              </Button>
            )}
          </>
        )}
      </Paper>
    </Stack>
  );
}
