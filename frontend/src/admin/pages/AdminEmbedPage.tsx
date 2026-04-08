import {
  useAdminEmbedApiKeys,
  useAdminEmbedSettings,
  useCreateAdminEmbedApiKeyMutation,
  useRevokeAdminEmbedApiKeyMutation,
  useRotateAdminEmbedWebhookMutation,
} from "@/hooks/useAdminEmbed";
import { useAdminSession } from "@/hooks/useAdminSession";
import { ApiErrorWithCode } from "@/api/client";
import { AdminSettingsSectionCard, ContextBar } from "@/shared/ui";
import {
  ActionIcon,
  Alert,
  Button,
  Code,
  CopyButton,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconCheck, IconCopy } from "@tabler/icons-react";
import { useState } from "react";

function copyField(label: string, value: string) {
  return (
    <Group gap="xs" wrap="nowrap" align="flex-start">
      <Text size="sm" w={140} c="dimmed" style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Code block style={{ flex: 1, wordBreak: "break-all", fontSize: 12 }}>
        {value}
      </Code>
      <CopyButton value={value} timeout={2000}>
        {({ copied, copy }: { copied: boolean; copy: () => void }) => (
          <Tooltip label={copied ? "Скопировано" : "Копировать"} withArrow>
            <ActionIcon color={copied ? "teal" : "gray"} variant="subtle" onClick={copy} aria-label="Копировать">
              {copied ? <IconCheck size={18} /> : <IconCopy size={18} />}
            </ActionIcon>
          </Tooltip>
        )}
      </CopyButton>
    </Group>
  );
}

export default function AdminEmbedPage() {
  const { data: adminSession } = useAdminSession();
  const orgId = adminSession?.organization_id ?? null;
  const orgReady = Boolean(orgId);
  const canManageEmbed = adminSession?.permissions?.includes("manage_embed_settings") ?? false;

  const settingsQ = useAdminEmbedSettings(orgReady);
  const keysQ = useAdminEmbedApiKeys(orgReady);
  const createKey = useCreateAdminEmbedApiKeyMutation();
  const revokeKey = useRevokeAdminEmbedApiKeyMutation();
  const rotateWh = useRotateAdminEmbedWebhookMutation();

  const [newLabel, setNewLabel] = useState("");
  const [tokenModal, tokenModalHandlers] = useDisclosure(false);
  const [whModal, whModalHandlers] = useDisclosure(false);
  const [shownToken, setShownToken] = useState<string | null>(null);
  const [shownWhSecret, setShownWhSecret] = useState<string | null>(null);

  const settingsErr =
    settingsQ.error instanceof ApiErrorWithCode ? settingsQ.error : null;
  const keysErr = keysQ.error instanceof ApiErrorWithCode ? keysQ.error : null;
  const isEntitlementDenied = (code: string | undefined) =>
    (code ?? "").toLowerCase() === "entitlement_required";

  const webhookBase =
    typeof window !== "undefined" ? `${window.location.origin}/api/v1/public/embed/v1/hooks` : "";
  const inboundToken = settingsQ.data?.inbound_route_token ?? "";
  const webhookUrl = inboundToken ? `${webhookBase}/${inboundToken}/inbox` : "";

  const handleCreateKey = () => {
    createKey.mutate(newLabel.trim() || null, {
      onSuccess: (data) => {
        setShownToken(data.token);
        setNewLabel("");
        tokenModalHandlers.open();
      },
    });
  };

  const handleRotateWebhook = () => {
    rotateWh.mutate(undefined, {
      onSuccess: (data) => {
        setShownWhSecret(data.webhook_secret);
        whModalHandlers.open();
      },
    });
  };

  return (
    <Stack gap="md">
      <ContextBar title="Встраивание (embed)" />

      {!orgReady ? (
        <Alert color="yellow" title="Нет привязки к организации">
          В сессии не указан <Code>organization_id</Code> (типично для legacy-установки или до провижининга SaaS).
          Раздел доступен после привязки администратора к организации и опции <Code>omni.embed.bundle</Code>.
        </Alert>
      ) : null}

      {isEntitlementDenied(settingsErr?.code) || isEntitlementDenied(keysErr?.code) ? (
        <Alert color="red" title="Нет опции тарифа">
          Требуется entitlement <Code>omni.embed.bundle</Code> для организации.
        </Alert>
      ) : null}

      {settingsErr && !isEntitlementDenied(settingsErr.code) ? (
        <Alert color="red" title="Не удалось загрузить настройки">
          {settingsErr.message}
        </Alert>
      ) : null}

      {keysErr && !isEntitlementDenied(keysErr.code) ? (
        <Alert color="red" title="Не удалось загрузить ключи">
          {keysErr.message}
        </Alert>
      ) : null}

      {orgReady && !canManageEmbed ? (
        <Alert color="gray" title="Только просмотр">
          Выпуск и отзыв ключей и ротация webhook — право <Code>manage_embed_settings</Code> (по умолчанию у владельца).
        </Alert>
      ) : null}

      <AdminSettingsSectionCard
        title="Webhook inbox"
        description="URL для внешних каналов (Bitrix24 и др.). После выпуска секрета передавайте его как Authorization: Bearer."
      >
        <Stack gap="sm">
          {webhookUrl ? copyField("POST URL", webhookUrl) : (
            <Text size="sm" c="dimmed">
              Загрузка…
            </Text>
          )}
          <Text size="sm" c="dimmed">
            Секрет:{" "}
            {settingsQ.data?.webhook_configured
              ? `выпущен (префикс ${settingsQ.data.webhook_bearer_prefix ?? "—"}…)`
              : "ещё не выпускали"}
          </Text>
          <Button
            variant="light"
            onClick={handleRotateWebhook}
            loading={rotateWh.isPending}
            disabled={!orgReady || !canManageEmbed}
          >
            Выпустить / сменить webhook secret
          </Button>
          <Text size="xs" c="dimmed">
            Опционально: <Code>X-Embed-Signature: v1=&lt;hmac_sha256_hex&gt;</Code> по raw body (ключ = тот же Bearer).
            Жёсткое требование — env <Code>EMBED_WEBHOOK_SIGNATURE_REQUIRED</Code>.
          </Text>
          <Text size="xs" c="dimmed">
            Идемпотентность: заголовки <Code>X-Embed-Idempotency-Key</Code> или <Code>Idempotency-Key</Code>.
          </Text>
        </Stack>
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="API keys (виджет / server-to-server)"
        description="Токен показывается один раз при создании. Формат dceb.&lt;id&gt;.&lt;secret&gt;."
      >
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="Метка (необязательно)"
              placeholder="production"
              value={newLabel}
              onChange={(e) => setNewLabel(e.currentTarget.value)}
              style={{ flex: "1 1 220px" }}
            />
            <Button onClick={handleCreateKey} loading={createKey.isPending} disabled={!orgReady || !canManageEmbed}>
              Создать ключ
            </Button>
          </Group>

          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Метка / префикс</Table.Th>
                <Table.Th>Создан</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th w={120} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(keysQ.data?.items ?? []).map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>
                    <Text size="sm">{row.label || "—"}</Text>
                    <Text size="xs" ff="monospace" component="span">
                      {row.key_prefix}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {row.created_at}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    {row.revoked_at ? (
                      <Text size="sm" c="dimmed">
                        Отозван
                      </Text>
                    ) : (
                      <Text size="sm" c="green">
                        Активен
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {!row.revoked_at ? (
                      <Button
                        size="xs"
                        variant="subtle"
                        color="red"
                        disabled={!canManageEmbed}
                        onClick={() => {
                          if (window.confirm("Отозвать ключ? Интеграции с ним перестанут работать.")) {
                            revokeKey.mutate(row.id);
                          }
                        }}
                        loading={revokeKey.isPending}
                      >
                        Отозвать
                      </Button>
                    ) : null}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          {keysQ.data?.items?.length === 0 ? (
            <Text size="sm" c="dimmed">
              Ключей пока нет.
            </Text>
          ) : null}
        </Stack>
      </AdminSettingsSectionCard>

      <Modal
        opened={tokenModal}
        onClose={() => {
          tokenModalHandlers.close();
          setShownToken(null);
        }}
        title="Сохраните API key"
        size="lg"
      >
        <Stack gap="md">
          <Alert color="orange">Этот токен больше не будет показан. Скопируйте сейчас.</Alert>
          {shownToken ? copyField("Token", shownToken) : null}
          <Button
            onClick={() => {
              tokenModalHandlers.close();
              setShownToken(null);
            }}
          >
            Готово
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={whModal}
        onClose={() => {
          whModalHandlers.close();
          setShownWhSecret(null);
        }}
        title="Webhook secret"
        size="lg"
      >
        <Stack gap="md">
          <Alert color="orange">Секрет показывается один раз. Укажите его в канале как Bearer.</Alert>
          {shownWhSecret ? copyField("Secret", shownWhSecret) : null}
          <Button
            onClick={() => {
              whModalHandlers.close();
              setShownWhSecret(null);
            }}
          >
            Готово
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
