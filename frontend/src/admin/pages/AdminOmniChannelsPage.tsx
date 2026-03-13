import { useState } from "react";
import {
  Badge,
  Box,
  Button,
  Flex,
  Grid,
  Group,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import {
  useCreateOwnerOmniChannel,
  useOwnerOmniChannels,
  useSetOwnerOmniChannelCredentials,
  useUpdateOwnerOmniChannel,
  type OwnerOmniChannel,
} from "@/hooks/useOwnerOmniChannels";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import { GlassModal } from "@/shared/ui/GlassModal";

const CHANNEL_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "TELEGRAM_BOT", label: "Telegram бот" },
  { value: "WHATSAPP_BUSINESS", label: "WhatsApp Business" },
  { value: "VIBER_BOT", label: "Viber бот" },
  { value: "VK_BOT", label: "VK бот" },
  { value: "MAX_CHAT", label: "Max чат" },
  { value: "SMS_GATEWAY", label: "SMS шлюз" },
  { value: "EMAIL_INBOX", label: "Email inbox" },
  { value: "OTHER", label: "Другое" },
];

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "PENDING_SETUP", label: "Ожидает настройки" },
  { value: "ACTIVE", label: "Активен" },
  { value: "DISABLED", label: "Отключен" },
  { value: "ERROR", label: "Ошибка" },
];

function getChannelTypeLabel(type: string): string {
  return CHANNEL_TYPE_OPTIONS.find((o) => o.value === type)?.label ?? type;
}

function getStatusLabel(status: string): string {
  return STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status;
}

function getProviderTypeForChannel(type: string): string {
  switch (type) {
    case "TELEGRAM_BOT":
      return "TELEGRAM";
    case "WHATSAPP_BUSINESS":
      return "WHATSAPP";
    case "VIBER_BOT":
      return "VIBER";
    case "VK_BOT":
      return "VK";
    case "MAX_CHAT":
      return "MAX";
    case "SMS_GATEWAY":
      return "SMS";
    case "EMAIL_INBOX":
      return "EMAIL";
    case "OTHER":
    default:
      return "OTHER";
  }
}

type CredentialsFormState = {
  bot_token: string;
  webhook_secret: string;
  admin_chat_id: string;
  api_url: string;
  api_token: string;
  phone_number_id: string;
  group_id: string;
  access_token: string;
  base_url: string;
  api_key: string;
  login: string;
  password: string;
  sender: string;
  imap_host: string;
  imap_port: string;
  imap_user: string;
  imap_password: string;
  inbox_email: string;
  other_json: string;
};

const initialCredentialsState: CredentialsFormState = {
  bot_token: "",
  webhook_secret: "",
  admin_chat_id: "",
  api_url: "",
  api_token: "",
  phone_number_id: "",
  group_id: "",
  access_token: "",
  base_url: "",
  api_key: "",
  login: "",
  password: "",
  sender: "",
  imap_host: "",
  imap_port: "",
  imap_user: "",
  imap_password: "",
  inbox_email: "",
  other_json: "{\n  \n}",
};

export default function AdminOmniChannelsPage() {
  const { data, isLoading, isError, error } = useOwnerOmniChannels();
  const createChannel = useCreateOwnerOmniChannel();
  const updateChannel = useUpdateOwnerOmniChannel();
  const setCredentials = useSetOwnerOmniChannelCredentials();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newType, setNewType] = useState<string | null>(null);
  const [newDisplayName, setNewDisplayName] = useState("");

  const [editingChannel, setEditingChannel] = useState<OwnerOmniChannel | null>(
    null,
  );
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editStatus, setEditStatus] = useState<string | null>(null);

  const [credentialsChannel, setCredentialsChannel] =
    useState<OwnerOmniChannel | null>(null);
  const [credentialsState, setCredentialsState] = useState<CredentialsFormState>(
    initialCredentialsState,
  );
  const [credentialsError, setCredentialsError] = useState<string | null>(null);

  const channels = data?.items ?? [];

  const handleOpenCreate = () => {
    setNewType("TELEGRAM_BOT");
    setNewDisplayName("");
    setIsCreateOpen(true);
  };

  const handleCreate = () => {
    if (!newType || !newDisplayName.trim()) return;
    createChannel.mutate(
      {
        type: newType,
        display_name: newDisplayName.trim(),
      },
      {
        onSuccess: () => {
          setIsCreateOpen(false);
          setNewDisplayName("");
        },
      },
    );
  };

  const handleOpenEdit = (channel: OwnerOmniChannel) => {
    setEditingChannel(channel);
    setEditDisplayName(channel.display_name);
    setEditStatus(channel.status);
  };

  const handleSaveEdit = () => {
    if (!editingChannel) return;
    updateChannel.mutate(
      {
        id: editingChannel.id,
        body: {
          display_name: editDisplayName.trim() || editingChannel.display_name,
          status: editStatus ?? editingChannel.status,
        },
      },
      {
        onSuccess: () => {
          setEditingChannel(null);
        },
      },
    );
  };

  const handleOpenCredentials = (channel: OwnerOmniChannel) => {
    setCredentialsError(null);
    setCredentialsChannel(channel);
    setCredentialsState(initialCredentialsState);
  };

  const handleChangeCredentialsField = <K extends keyof CredentialsFormState>(
    key: K,
    value: string,
  ) => {
    setCredentialsState((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveCredentials = () => {
    if (!credentialsChannel) return;
    setCredentialsError(null);
    try {
      const type = credentialsChannel.type;
      let payload: Record<string, unknown> = {};

      if (type === "TELEGRAM_BOT") {
        payload = {
          bot_token: credentialsState.bot_token || undefined,
          webhook_secret: credentialsState.webhook_secret || undefined,
          admin_chat_id: credentialsState.admin_chat_id?.trim() || undefined,
        };
      } else if (type === "WHATSAPP_BUSINESS") {
        payload = {
          api_url: credentialsState.api_url || undefined,
          api_token: credentialsState.api_token || undefined,
          phone_number_id: credentialsState.phone_number_id || undefined,
        };
      } else if (type === "VIBER_BOT") {
        payload = {
          bot_token: credentialsState.bot_token || undefined,
        };
      } else if (type === "VK_BOT") {
        payload = {
          group_id: credentialsState.group_id || undefined,
          access_token: credentialsState.access_token || undefined,
        };
      } else if (type === "MAX_CHAT") {
        payload = {
          base_url: credentialsState.base_url || undefined,
          api_key: credentialsState.api_key || undefined,
          webhook_secret: credentialsState.webhook_secret || undefined,
        };
      } else if (type === "SMS_GATEWAY") {
        payload = {
          login: credentialsState.login || undefined,
          password: credentialsState.password || undefined,
          sender: credentialsState.sender || undefined,
        };
      } else if (type === "EMAIL_INBOX") {
        payload = {
          imap_host: credentialsState.imap_host || undefined,
          imap_port: credentialsState.imap_port
            ? Number(credentialsState.imap_port)
            : undefined,
          imap_user: credentialsState.imap_user || undefined,
          imap_password: credentialsState.imap_password || undefined,
          inbox_email: credentialsState.inbox_email || undefined,
        };
      } else {
        const raw = credentialsState.other_json || "{}";
        try {
          payload = JSON.parse(raw);
        } catch (e) {
          setCredentialsError("Некорректный JSON. Проверьте формат.");
          return;
        }
      }

      const provider_type = getProviderTypeForChannel(type);
      const payloadString = JSON.stringify(payload);

      setCredentials.mutate(
        {
          id: credentialsChannel.id,
          body: {
            provider_type,
            scopes: null,
            payload: payloadString,
          },
        },
        {
          onSuccess: () => {
            setCredentialsChannel(null);
          },
          onError: (err: Error) => {
            setCredentialsError(err?.message ?? "Не удалось сохранить ключи. Попробуйте ещё раз.");
          },
        },
      );
    } catch (e) {
      setCredentialsError("Не удалось сохранить ключи. Попробуйте ещё раз.");
    }
  };

  if (isLoading) {
    return (
      <Stack>
        <Title order={3}>Омниканальные каналы</Title>
        <DataSkeleton lines={5} />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <Title order={3}>Омниканальные каналы</Title>
        <Text c="red">
          {error instanceof Error ? error.message : "Ошибка загрузки каналов"}
        </Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Title order={3}>Омниканальные каналы</Title>
      <Text size="sm" c="dimmed">
        Здесь вы подключаете каналы, через которые клиенты пишут вам (Telegram,
        WhatsApp, VK, Viber, Max, SMS, email, другие). Все сообщения из них
        будут стекаться в раздел «Единый чат».
      </Text>

      <Group justify="space-between" align="center">
        <Text size="sm" c="dimmed">
          Всего каналов: {channels.length}
        </Text>
        <Button onClick={handleOpenCreate} size="sm">
          Добавить канал
        </Button>
      </Group>

      {!channels.length ? (
        <EmptyState
          title="Каналов ещё нет"
          subtitle="Создайте первый канал, чтобы подключить мессенджеры и другие источники."
        />
      ) : (
        <Paper withBorder radius="md" p="sm">
          <Table striped highlightOnHover withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Тип</Table.Th>
                <Table.Th>Отображаемое имя</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Подключено</Table.Th>
                <Table.Th style={{ width: 220 }}>Действия</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {channels.map((ch) => (
                <Table.Tr key={ch.id}>
                  <Table.Td>
                    <Stack gap={2} justify="center">
                      <Text size="sm" fw={500}>
                        {getChannelTypeLabel(ch.type)}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {ch.type}
                      </Text>
                    </Stack>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{ch.display_name}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="sm" variant="light">
                      {getStatusLabel(ch.status)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      size="sm"
                      color={ch.has_credentials ? "green" : "gray"}
                      variant={ch.has_credentials ? "filled" : "light"}
                    >
                      {ch.has_credentials ? "Подключено" : "Не настроено"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Flex gap="xs" wrap="wrap">
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => handleOpenEdit(ch)}
                      >
                        Редактировать
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => handleOpenCredentials(ch)}
                      >
                        Настроить ключи
                      </Button>
                    </Flex>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      <GlassModal
        opened={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Добавить омниканальный канал"
        centered
      >
        <Stack gap="md">
          <Select
            label="Тип канала"
            data={CHANNEL_TYPE_OPTIONS}
            value={newType}
            onChange={setNewType}
          />
          <TextInput
            label="Отображаемое имя"
            placeholder="Например, Telegram клиники"
            value={newDisplayName}
            onChange={(e) => setNewDisplayName(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button
              variant="default"
              onClick={() => setIsCreateOpen(false)}
              size="sm"
            >
              Отмена
            </Button>
            <Button
              onClick={handleCreate}
              loading={createChannel.isPending}
              size="sm"
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={!!editingChannel}
        onClose={() => setEditingChannel(null)}
        title="Редактирование канала"
        centered
      >
        {editingChannel && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              {getChannelTypeLabel(editingChannel.type)} ({editingChannel.type})
            </Text>
            <TextInput
              label="Отображаемое имя"
              value={editDisplayName}
              onChange={(e) => setEditDisplayName(e.currentTarget.value)}
            />
            <Select
              label="Статус"
              data={STATUS_OPTIONS}
              value={editStatus}
              onChange={setEditStatus}
            />
            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                onClick={() => setEditingChannel(null)}
                size="sm"
              >
                Отмена
              </Button>
              <Button
                onClick={handleSaveEdit}
                loading={updateChannel.isPending}
                size="sm"
              >
                Сохранить
              </Button>
            </Group>
          </Stack>
        )}
      </GlassModal>

      <GlassModal
        opened={!!credentialsChannel}
        onClose={() => setCredentialsChannel(null)}
        title={
          credentialsChannel
            ? `Настройка ключей: ${credentialsChannel.display_name}`
            : "Настройка ключей"
        }
        centered
        size="lg"
      >
        {credentialsChannel && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Тип: {getChannelTypeLabel(credentialsChannel.type)} (
              {credentialsChannel.type})
            </Text>

            {credentialsChannel.type === "TELEGRAM_BOT" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label="Bot token"
                    type="password"
                    placeholder="123456:ABC..."
                    description="Токен бота от @BotFather. Используется для отправки сообщений клиентам. Никому не передавайте этот токен."
                    value={credentialsState.bot_token}
                    onChange={(e) =>
                      handleChangeCredentialsField("bot_token", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Webhook secret (опционально)"
                    description="Необязательный секрет для проверки вебхуков Telegram (заголовок X-Telegram-Bot-Api-Secret-Token). Укажите ту же строку, что задали в настройках вебхука бота."
                    value={credentialsState.webhook_secret}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "webhook_secret",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="ID чата админа (для оповещений)"
                    placeholder="-1001234567890 или 123456789"
                    description="Личный чат или группа в Telegram, куда бот будет присылать оповещения (запрос оператора, черновики AI, при включении — уведомления о записях). Узнать ID: напишите боту @userinfobot в нужный чат или посмотрите update.message.chat.id в вебхуке."
                    value={credentialsState.admin_chat_id}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "admin_chat_id",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
              </Grid>
            )}

            {credentialsChannel.type === "WHATSAPP_BUSINESS" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label="API URL"
                    placeholder="https://graph.facebook.com/v20.0/..."
                    description="Базовый URL WhatsApp Cloud API для отправки сообщений. Например: https://graph.facebook.com/v20.0/<PHONE_NUMBER_ID>/messages. Скопируйте из примеров в кабинете Meta Developers."
                    value={credentialsState.api_url}
                    onChange={(e) =>
                      handleChangeCredentialsField("api_url", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="API token"
                    type="password"
                    description="Постоянный Access Token WhatsApp Cloud API из кабинета Meta (раздел Access Tokens). Используется для авторизации при отправке сообщений."
                    value={credentialsState.api_token}
                    onChange={(e) =>
                      handleChangeCredentialsField("api_token", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Phone number ID"
                    description="ID бизнес-номера WhatsApp (Phone Number ID), не сам номер. Найдите в разделе WhatsApp → Phone numbers в Meta Developers."
                    value={credentialsState.phone_number_id}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "phone_number_id",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
              </Grid>
            )}

            {credentialsChannel.type === "VIBER_BOT" && (
              <TextInput
                label="Bot token"
                type="password"
                description="Authentication token Viber-бота. Скопируйте из кабинета Viber (Bot Settings → Authentication token). Передаётся в заголовке X-Viber-Auth-Token при отправке сообщений и установке вебхука."
                value={credentialsState.bot_token}
                onChange={(e) =>
                  handleChangeCredentialsField("bot_token", e.currentTarget.value)
                }
              />
            )}

            {credentialsChannel.type === "VK_BOT" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label="Group ID"
                    description="ID сообщества VK (group_id), от имени которого бот ведёт переписку. Скопируйте число из адреса группы или раздела API в настройках сообщества."
                    value={credentialsState.group_id}
                    onChange={(e) =>
                      handleChangeCredentialsField("group_id", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Access token"
                    type="password"
                    description="Access token сообщества VK с правами на сообщения (messages). Создаётся в настройках сообщества → Работа с API → Ключи доступа. Не путайте с токеном пользователя."
                    value={credentialsState.access_token}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "access_token",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
              </Grid>
            )}

            {credentialsChannel.type === "MAX_CHAT" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label="Base URL"
                    placeholder="https://max-chat.example.com"
                    description="Базовый URL API внешнего чат-сервиса (Max Chat). Например: https://max-chat.example.com/api. Уточните адрес в документации провайдера."
                    value={credentialsState.base_url}
                    onChange={(e) =>
                      handleChangeCredentialsField("base_url", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="API key"
                    type="password"
                    description="API key (секретный токен) для доступа к Max Chat. Скопируйте из личного кабинета сервиса. Хранится в зашифрованном виде."
                    value={credentialsState.api_key}
                    onChange={(e) =>
                      handleChangeCredentialsField("api_key", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Webhook secret"
                    description="Необязательный секрет для проверки входящих вебхуков Max Chat. Укажите ту же строку, что настроена в вебхуках сервиса."
                    value={credentialsState.webhook_secret}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "webhook_secret",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
              </Grid>
            )}

            {credentialsChannel.type === "SMS_GATEWAY" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label="Логин"
                    description="Логин учётной записи SMS-провайдера (например, SMSC.ru). Используется для авторизации при отправке SMS."
                    value={credentialsState.login}
                    onChange={(e) =>
                      handleChangeCredentialsField("login", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Пароль"
                    type="password"
                    description="Пароль или API-ключ для HTTP API SMS-провайдера. При наличии используйте выданный провайдером API-ключ, а не пароль от личного кабинета."
                    value={credentialsState.password}
                    onChange={(e) =>
                      handleChangeCredentialsField("password", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Имя отправителя"
                    description="Имя отправителя в SMS (от кого). Должно быть согласовано и активировано у SMS-провайдера (например, «CLINIC»)."
                    value={credentialsState.sender}
                    onChange={(e) =>
                      handleChangeCredentialsField("sender", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
              </Grid>
            )}

            {credentialsChannel.type === "EMAIL_INBOX" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label="IMAP host"
                    placeholder="imap.gmail.com"
                    description="IMAP-сервер почтового ящика. Уточните у почтового провайдера (например, imap.gmail.com, imap.mail.ru)."
                    value={credentialsState.imap_host}
                    onChange={(e) =>
                      handleChangeCredentialsField("imap_host", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="IMAP port"
                    placeholder="993"
                    description="Порт IMAP (обычно 993 для IMAPS). Уточните в настройках почтового провайдера."
                    value={credentialsState.imap_port}
                    onChange={(e) =>
                      handleChangeCredentialsField("imap_port", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="Email (inbox)"
                    placeholder="inbox@example.com"
                    description="Адрес этого ящика. На него пользователи пишут письма, которые попадают в единый чат."
                    value={credentialsState.inbox_email}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "inbox_email",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="IMAP user"
                    description="Логин почтового ящика для входа по IMAP (часто полный адрес user@example.com)."
                    value={credentialsState.imap_user}
                    onChange={(e) =>
                      handleChangeCredentialsField("imap_user", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="IMAP password"
                    type="password"
                    description="Пароль почтового ящика или пароль приложений (app password), если провайдер его требует."
                    value={credentialsState.imap_password}
                    onChange={(e) =>
                      handleChangeCredentialsField(
                        "imap_password",
                        e.currentTarget.value,
                      )
                    }
                  />
                </Grid.Col>
              </Grid>
            )}

            {credentialsChannel.type === "OTHER" && (
              <Box>
                <Textarea
                  label="Произвольный JSON для провайдера"
                  description="Произвольный JSON с настройками интеграции. Используйте только по инструкции разработчика: формат зависит от конкретного провайдера."
                  minRows={6}
                  value={credentialsState.other_json}
                  onChange={(e) =>
                    handleChangeCredentialsField(
                      "other_json",
                      e.currentTarget.value,
                    )
                  }
                />
              </Box>
            )}

            {credentialsError && (
              <Text c="red" size="sm">
                {credentialsError}
              </Text>
            )}

            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                onClick={() => setCredentialsChannel(null)}
                size="sm"
              >
                Отмена
              </Button>
              <Button
                onClick={handleSaveCredentials}
                loading={setCredentials.isPending}
                size="sm"
              >
                Сохранить
              </Button>
            </Group>
          </Stack>
        )}
      </GlassModal>
    </Stack>
  );
}

