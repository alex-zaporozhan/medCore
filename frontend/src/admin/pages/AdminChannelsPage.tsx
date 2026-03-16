import {
  useChannelConfigs,
  useUpsertChannelConfig,
  type NotificationChannelConfigRead,
} from "@/hooks/useChannelConfigs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Alert,
  Button,
  Card,
  Group,
  NumberInput,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { useEffect, useState } from "react";

type ChannelType = "telegram" | "sms" | "email";

function getConfigByChannel(
  list: NotificationChannelConfigRead[] | undefined,
  channel: ChannelType
): NotificationChannelConfigRead | undefined {
  return list?.find((c) => c.channel === channel);
}

function ChannelCard({
  channel,
  label,
  config,
  onSave,
  isSaving,
}: {
  channel: ChannelType;
  label: string;
  config: NotificationChannelConfigRead | undefined;
  onSave: (enabled: boolean, configJson: Record<string, unknown>) => void;
  isSaving: boolean;
}) {
  const c = config?.config_json as Record<string, unknown> | undefined;
  const [enabled, setEnabled] = useState(config?.enabled ?? false);
  const [botToken, setBotToken] = useState((c?.bot_token as string) ?? "");
  const [adminChatId, setAdminChatId] = useState((c?.admin_chat_id as string) ?? "");
  const [login, setLogin] = useState((c?.login as string) ?? "");
  const [password, setPassword] = useState((c?.password as string) ?? "");
  const [sender, setSender] = useState((c?.sender as string) ?? "");
  const [smtpHost, setSmtpHost] = useState((c?.smtp_host as string) ?? "");
  const [smtpPort, setSmtpPort] = useState((c?.smtp_port as number) ?? 587);
  const [smtpUser, setSmtpUser] = useState((c?.smtp_user as string) ?? "");
  const [smtpPassword, setSmtpPassword] = useState((c?.smtp_password as string) ?? "");
  const [fromEmail, setFromEmail] = useState((c?.from_email as string) ?? "");

  useEffect(() => {
    const cfg = config?.config_json as Record<string, unknown> | undefined;
    setEnabled(config?.enabled ?? false);
    setBotToken((cfg?.bot_token as string) ?? "");
    setAdminChatId((cfg?.admin_chat_id as string) ?? "");
    setLogin((cfg?.login as string) ?? "");
    setPassword((cfg?.password as string) ?? "");
    setSender((cfg?.sender as string) ?? "");
    setSmtpHost((cfg?.smtp_host as string) ?? "");
    setSmtpPort((cfg?.smtp_port as number) ?? 587);
    setSmtpUser((cfg?.smtp_user as string) ?? "");
    setSmtpPassword((cfg?.smtp_password as string) ?? "");
    setFromEmail((cfg?.from_email as string) ?? "");
  }, [config?.enabled, config?.config_json, config?.updated_at]);

  const handleSave = () => {
    if (channel === "telegram") {
      onSave(enabled, { bot_token: botToken || undefined, admin_chat_id: adminChatId || undefined });
    } else if (channel === "sms") {
      onSave(enabled, { login: login || undefined, password: password || undefined, sender: sender || undefined });
    } else {
      onSave(enabled, {
        smtp_host: smtpHost || undefined,
        smtp_port: smtpPort,
        smtp_user: smtpUser || undefined,
        smtp_password: smtpPassword || undefined,
        from_email: fromEmail || undefined,
      });
    }
  };

  return (
    <Card withBorder p="md" radius="md">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={5}>{label}</Title>
          <Switch
            label="Включено"
            checked={enabled}
            onChange={(e) => setEnabled(e.currentTarget.checked)}
          />
        </Group>
        {channel === "telegram" && (
          <>
            <TextInput
              label="Токен бота"
              placeholder="123456:ABC..."
              value={botToken}
              onChange={(e) => setBotToken(e.currentTarget.value)}
              type="password"
            />
            <TextInput
              label="ID чата администратора"
              placeholder="-1001234567890"
              value={adminChatId}
              onChange={(e) => setAdminChatId(e.currentTarget.value)}
            />
          </>
        )}
        {channel === "sms" && (
          <>
            <TextInput
              label="Логин (SMSC)"
              value={login}
              onChange={(e) => setLogin(e.currentTarget.value)}
            />
            <TextInput
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
            />
            <TextInput
              label="Имя отправителя"
              placeholder="CLINIC"
              value={sender}
              onChange={(e) => setSender(e.currentTarget.value)}
            />
          </>
        )}
        {channel === "email" && (
          <>
            <TextInput
              label="SMTP сервер"
              placeholder="smtp.gmail.com"
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.currentTarget.value)}
            />
            <NumberInput
              label="Порт"
              min={1}
              max={65535}
              value={smtpPort}
              onChange={(v) => setSmtpPort(Number(v) || 587)}
            />
            <TextInput
              label="Пользователь"
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.currentTarget.value)}
            />
            <TextInput
              label="Пароль"
              type="password"
              value={smtpPassword}
              onChange={(e) => setSmtpPassword(e.currentTarget.value)}
            />
            <TextInput
              label="От кого (email)"
              placeholder="noreply@clinic.local"
              value={fromEmail}
              onChange={(e) => setFromEmail(e.currentTarget.value)}
            />
          </>
        )}
        <Button onClick={handleSave} loading={isSaving} size="xs">
          Сохранить
        </Button>
      </Stack>
    </Card>
  );
}

export default function AdminChannelsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const { data: configs, isLoading, isError, error } = useChannelConfigs(clinicId);
  const upsertMut = useUpsertChannelConfig(clinicId);

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Каналы уведомлений" />
        <EmptyStateHint title="Выберите клинику" />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <ContextBar title="Каналы уведомлений" />
        <Alert color="red" title="Ошибка">
          {error?.message ?? "Не удалось загрузить настройки каналов."}
        </Alert>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Каналы уведомлений" />
        <PageSkeleton variant="table" rows={5} />
      </Stack>
    );
  }

  const list = configs ?? [];

  const handleSave = (channel: ChannelType, enabled: boolean, configJson: Record<string, unknown>) => {
    upsertMut.mutate({
      channel,
      body: { channel, enabled, config_json: configJson },
    });
  };

  return (
    <Stack>
      <ContextBar title="Каналы уведомлений" />
      <Text size="sm" c="dimmed">
        Настройка Telegram, SMS и Email для напоминаний и уведомлений. Данные хранятся для выбранной клиники.
      </Text>
      <Stack gap="md" style={{ maxWidth: 480 }}>
        <ChannelCard
          channel="telegram"
          label="Telegram"
          config={getConfigByChannel(list, "telegram")}
          onSave={(enabled, configJson) => handleSave("telegram", enabled, configJson)}
          isSaving={upsertMut.isPending}
        />
        <ChannelCard
          channel="sms"
          label="SMS (SMSC.ru)"
          config={getConfigByChannel(list, "sms")}
          onSave={(enabled, configJson) => handleSave("sms", enabled, configJson)}
          isSaving={upsertMut.isPending}
        />
        <ChannelCard
          channel="email"
          label="Email (SMTP)"
          config={getConfigByChannel(list, "email")}
          onSave={(enabled, configJson) => handleSave("email", enabled, configJson)}
          isSaving={upsertMut.isPending}
        />
      </Stack>
    </Stack>
  );
}
