import { useMemo, useState } from "react";
import {
  Alert,
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
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import { ContextBar } from "@/shared/ui/ContextBar";
import {
  omniChannelCreateTypeOptions,
  omniChannelStatusLabel,
  omniChannelStatusOptions,
  omniChannelTypeLabel,
  isOmniChannelCreatableType,
} from "@/shared/chatI18n";
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
import { QueryErrorAlert } from "@/shared/ui";

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
  const { t, i18n } = useTranslation("chat");
  const channelTypeCreateOptions = useMemo(() => omniChannelCreateTypeOptions(), [i18n.language]);
  const statusOptions = useMemo(() => omniChannelStatusOptions(), [i18n.language]);

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
    if (!isOmniChannelCreatableType(newType)) return;
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
    if (credentialsChannel.type === "VK_BOT") return;
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
        } catch {
          setCredentialsError(t("errors.invalidJson"));
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
            setCredentialsError(err?.message ?? t("errors.saveKeysFailed"));
          },
        },
      );
    } catch {
      setCredentialsError(t("errors.saveKeysFailed"));
    }
  };

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title={t("omniChannels.title")} />
        <DataSkeleton lines={5} />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <ContextBar title={t("omniChannels.title")} />
        <QueryErrorAlert error={error} title={t("errors.loadOmniChannelsFailed")} />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <ContextBar
        title={t("omniChannels.title")}
        actions={
          <Button onClick={handleOpenCreate} size="sm">
            {t("omniChannels.add")}
          </Button>
        }
      />
      <Text size="sm" c="dimmed">
        {t("omniChannels.intro")}
      </Text>

      <Text size="sm" c="dimmed" mb="sm">
        {t("omniChannels.total", { count: channels.length })}
      </Text>

      {!channels.length ? (
        <EmptyState title={t("omniChannels.emptyTitle")} subtitle={t("omniChannels.emptyHint")} />
      ) : (
        <Paper withBorder radius="md" p="sm">
          <Table striped highlightOnHover withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("omniChannels.colType")}</Table.Th>
                <Table.Th>{t("omniChannels.colName")}</Table.Th>
                <Table.Th>{t("omniChannels.colStatus")}</Table.Th>
                <Table.Th>{t("omniChannels.colConnected")}</Table.Th>
                <Table.Th style={{ width: 220 }}>{t("omniChannels.colActions")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {channels.map((ch) => (
                <Table.Tr key={ch.id}>
                  <Table.Td>
                    <Stack gap={2} justify="center">
                      <Text size="sm" fw={500}>
                        {omniChannelTypeLabel(ch.type)}
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
                      {omniChannelStatusLabel(ch.status)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      size="sm"
                      color={ch.has_credentials ? "green" : "gray"}
                      variant={ch.has_credentials ? "filled" : "light"}
                    >
                      {ch.has_credentials ? t("omniChannels.connected") : t("omniChannels.notConfigured")}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Flex gap="xs" wrap="wrap">
                      <Button size="xs" variant="light" onClick={() => handleOpenEdit(ch)}>
                        {t("edit")}
                      </Button>
                      <Button size="xs" variant="outline" onClick={() => handleOpenCredentials(ch)}>
                        {t("omniChannels.setupKeys")}
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
        title={t("omniChannels.addTitle")}
        centered
      >
        <Stack gap="md">
          <Select
            label={t("omniChannels.type")}
            data={channelTypeCreateOptions}
            value={newType}
            onChange={setNewType}
          />
          <TextInput
            label={t("omniChannels.displayName")}
            placeholder={t("omniChannels.displayNamePlaceholder")}
            value={newDisplayName}
            onChange={(e) => setNewDisplayName(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setIsCreateOpen(false)} size="sm">
              {t("cancel")}
            </Button>
            <Button onClick={handleCreate} loading={createChannel.isPending} size="sm">
              {t("create")}
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={!!editingChannel}
        onClose={() => setEditingChannel(null)}
        title={t("omniChannels.editTitle")}
        centered
      >
        {editingChannel && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              {t("omniChannels.typeLine", {
                label: omniChannelTypeLabel(editingChannel.type),
                code: editingChannel.type,
              })}
            </Text>
            <TextInput
              label={t("omniChannels.displayName")}
              value={editDisplayName}
              onChange={(e) => setEditDisplayName(e.currentTarget.value)}
            />
            <Select
              label={t("omniChannels.colStatus")}
              data={statusOptions}
              value={editStatus}
              onChange={setEditStatus}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setEditingChannel(null)} size="sm">
                {t("cancel")}
              </Button>
              <Button onClick={handleSaveEdit} loading={updateChannel.isPending} size="sm">
                {t("save")}
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
            ? t("omniChannels.keysTitleNamed", { name: credentialsChannel.display_name })
            : t("omniChannels.keysTitle")
        }
        centered
        size="lg"
      >
        {credentialsChannel && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              {t("omniChannels.typeLine", {
                label: omniChannelTypeLabel(credentialsChannel.type),
                code: credentialsChannel.type,
              })}
            </Text>

            {credentialsChannel.type === "TELEGRAM_BOT" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.botToken")}
                    type="password"
                    placeholder="123456:ABC..."
                    description={t("credentials.telegramBotDesc")}
                    value={credentialsState.bot_token}
                    onChange={(e) =>
                      handleChangeCredentialsField("bot_token", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.webhookSecretOptional")}
                    description={t("credentials.telegramWebhookDesc")}
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
                    label={t("credentials.adminChatId")}
                    placeholder={t("credentials.adminChatIdPlaceholder")}
                    description={t("credentials.telegramAdminChatDesc")}
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
                    label={t("credentials.apiUrl")}
                    placeholder="https://graph.facebook.com/v20.0/..."
                    description={t("credentials.whatsappUrlDesc")}
                    value={credentialsState.api_url}
                    onChange={(e) =>
                      handleChangeCredentialsField("api_url", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.apiToken")}
                    type="password"
                    description={t("credentials.whatsappTokenDesc")}
                    value={credentialsState.api_token}
                    onChange={(e) =>
                      handleChangeCredentialsField("api_token", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.phoneNumberId")}
                    description={t("credentials.whatsappPhoneDesc")}
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
                label={t("credentials.botToken")}
                type="password"
                description={t("credentials.viberTokenDesc")}
                value={credentialsState.bot_token}
                onChange={(e) =>
                  handleChangeCredentialsField("bot_token", e.currentTarget.value)
                }
              />
            )}

            {credentialsChannel.type === "VK_BOT" && (
              <Stack gap="sm">
                <Alert color="gray" variant="light">
                  {t("credentials.otherJsonDesc")}
                </Alert>
                <Textarea
                  label={t("credentials.otherJson")}
                  minRows={6}
                  value={credentialsState.other_json}
                  readOnly
                  disabled
                />
              </Stack>
            )}

            {credentialsChannel.type === "MAX_CHAT" && (
              <Grid gutter="sm">
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.baseUrl")}
                    placeholder="https://max-chat.example.com"
                    description={t("credentials.maxUrlDesc")}
                    value={credentialsState.base_url}
                    onChange={(e) =>
                      handleChangeCredentialsField("base_url", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.apiKey")}
                    type="password"
                    description={t("credentials.maxKeyDesc")}
                    value={credentialsState.api_key}
                    onChange={(e) =>
                      handleChangeCredentialsField("api_key", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.webhookSecret")}
                    description={t("credentials.maxWebhookDesc")}
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
                    label={t("login")}
                    description={t("credentials.smsLoginDesc")}
                    value={credentialsState.login}
                    onChange={(e) =>
                      handleChangeCredentialsField("login", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("password")}
                    type="password"
                    description={t("credentials.smsPasswordDesc")}
                    value={credentialsState.password}
                    onChange={(e) =>
                      handleChangeCredentialsField("password", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label={t("credentials.sender")}
                    description={t("credentials.smsSenderDesc")}
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
                    label={t("credentials.imapHost")}
                    placeholder="imap.gmail.com"
                    description={t("credentials.imapHostDesc")}
                    value={credentialsState.imap_host}
                    onChange={(e) =>
                      handleChangeCredentialsField("imap_host", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label={t("credentials.imapPort")}
                    placeholder="993"
                    description={t("credentials.imapPortDesc")}
                    value={credentialsState.imap_port}
                    onChange={(e) =>
                      handleChangeCredentialsField("imap_port", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label={t("credentials.inboxEmail")}
                    placeholder="inbox@example.com"
                    description={t("credentials.inboxEmailDesc")}
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
                    label={t("credentials.imapUser")}
                    description={t("credentials.imapUserDesc")}
                    value={credentialsState.imap_user}
                    onChange={(e) =>
                      handleChangeCredentialsField("imap_user", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label={t("credentials.imapPassword")}
                    type="password"
                    description={t("credentials.imapPasswordDesc")}
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
                  label={t("credentials.otherJson")}
                  description={t("credentials.otherJsonDesc")}
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
              <Alert color="red" variant="light" title={t("error")}>
                {credentialsError}
              </Alert>
            )}

            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                onClick={() => setCredentialsChannel(null)}
                size="sm"
              >
                {t("cancel")}
              </Button>
              {credentialsChannel.type !== "VK_BOT" ? (
                <Button
                  onClick={handleSaveCredentials}
                  loading={setCredentials.isPending}
                  size="sm"
                >
                  {t("save")}
                </Button>
              ) : null}
            </Group>
          </Stack>
        )}
      </GlassModal>
    </Stack>
  );
}

