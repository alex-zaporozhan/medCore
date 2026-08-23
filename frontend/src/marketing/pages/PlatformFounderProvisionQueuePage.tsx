import { API_BASE } from "@/api/client";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import { FounderQueryError, formatPlatformFounderApiError, founderFailMessage } from "@/marketing/platformFounderApi";
import {
  ActionIcon,
  Accordion,
  Button,
  Container,
  CopyButton,
  Group,
  Modal,
  Paper,
  PasswordInput,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconCheck, IconCopy } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

function ShortUuidCell({ id, label }: { id: string | null; label: string }) {
  const { t } = useTranslation("founder");
  if (!id) {
    return <Text size="xs">—</Text>;
  }
  return (
    <Group gap={6} wrap="nowrap" align="center">
      <Tooltip label={id} withArrow>
        <Text size="xs" ff="monospace" style={{ cursor: "default" }}>
          {id.length > 10 ? `${id.slice(0, 8)}…` : id}
        </Text>
      </Tooltip>
      <CopyButton value={id} timeout={2000}>
        {({ copied, copy }) => (
          <Tooltip label={copied ? t("queue.copied") : t("queue.copy", { label })}>
            <ActionIcon size="sm" variant="subtle" onClick={copy} aria-label={t("queue.copy", { label })}>
              {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
            </ActionIcon>
          </Tooltip>
        )}
      </CopyButton>
    </Group>
  );
}

type QueueItem = {
  intent_id: string;
  status: string;
  email: string | null;
  organization_id: string | null;
  provision_retry_count: number;
  provision_next_attempt_at: string | null;
  provision_last_error: string | null;
  provision_dead_letter: boolean;
  paid_at: string | null;
  billing_revoked_at: string | null;
};

/**
 * Очередь signup / провижининг (FE-E2). Токен — из сессии входа; опционально ручная подмена для ops.
 */
export default function PlatformFounderProvisionQueuePage() {
  const { t } = useTranslation("founder");
  const { token, setToken } = usePlatformFounderSession();
  const queryClient = useQueryClient();
  const [manualToken, setManualToken] = useState("");
  const [tokenVisible, setTokenVisible] = useState(false);

  const queueQ = useQuery({
    queryKey: ["platform-founder", "provision-queue", token],
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/provision-queue`, {
        headers: { Authorization: `Bearer ${token.trim()}` },
      });
      if (r.status === 401 || r.status === 403) {
        throw new FounderQueryError("wrongToken");
      }
      if (r.status === 503) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("serviceDisabled", { apiDetail: apiDetail || undefined });
      }
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      const data = (await r.json()) as QueueItem[];
      return Array.isArray(data) ? data : [];
    },
    enabled: !!token.trim(),
  });

  const retryMut = useMutation({
    mutationFn: async (intentId: string) => {
      const r = await fetch(
        `${API_BASE}/v1/platform/internal/signup-intents/${intentId}/retry-provision`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token.trim()}` },
        },
      );
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        if (r.status === 409) {
          throw new FounderQueryError("retryConflict", { apiDetail: apiDetail || undefined });
        }
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["platform-founder", "provision-queue", token] });
      void queryClient.invalidateQueries({ queryKey: ["platform-founder", "health", token] });
    },
  });

  const [manualCloseIntentId, setManualCloseIntentId] = useState<string | null>(null);
  const [manualCloseNote, setManualCloseNote] = useState("");

  const manualCloseMut = useMutation({
    mutationFn: async ({ intentId, note }: { intentId: string; note: string }) => {
      const r = await fetch(
        `${API_BASE}/v1/platform/internal/signup-intents/${intentId}/manual-close`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token.trim()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ note: note.trim() || null }),
        },
      );
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        if (r.status === 409) {
          throw new FounderQueryError("closeConflict", { apiDetail: apiDetail || undefined });
        }
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
    },
    onSuccess: () => {
      setManualCloseIntentId(null);
      setManualCloseNote("");
      void queryClient.invalidateQueries({ queryKey: ["platform-founder", "provision-queue", token] });
    },
  });

  const applyManualToken = useCallback(() => {
    setToken(manualToken);
    setManualToken("");
  }, [manualToken, setToken]);

  const rows = queueQ.data ?? [];
  const errorMsg = founderFailMessage(
    queueQ.error ?? retryMut.error ?? manualCloseMut.error ?? null,
    t,
  );
  const errorShown =
    queueQ.error || retryMut.error || manualCloseMut.error ? errorMsg : null;

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>{t("queue.title")}</Title>
          <Text size="sm" c="dimmed" mt={4}>
            {t("queue.lead")}
          </Text>
        </div>

        <Paper p="md" radius="md" withBorder>
          <Stack gap="sm">
            <Group>
              <Button variant="light" loading={queueQ.isFetching} onClick={() => void queueQ.refetch()}>
                {t("queue.refresh")}
              </Button>
            </Group>
            {errorShown ? (
              <Text size="sm" c="red">
                {errorShown}
              </Text>
            ) : null}
            <Accordion variant="contained">
              <Accordion.Item value="manual-token">
                <Accordion.Control>{t("queue.manualToken")}</Accordion.Control>
                <Accordion.Panel>
                  <Stack gap="sm">
                    <PasswordInput
                      label={t("queue.pasteJwt")}
                      value={manualToken}
                      onChange={(e) => setManualToken(e.currentTarget.value)}
                      visible={tokenVisible}
                      onVisibilityChange={setTokenVisible}
                      autoComplete="off"
                    />
                    <Button variant="outline" onClick={applyManualToken}>
                      {t("queue.applySession")}
                    </Button>
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          </Stack>
        </Paper>

        <Modal
          opened={manualCloseIntentId !== null}
          onClose={() => {
            if (!manualCloseMut.isPending) {
              setManualCloseIntentId(null);
              setManualCloseNote("");
            }
          }}
          title={t("queue.closeModalTitle")}
          size="md"
        >
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              {t("queue.closeModalLead")}
            </Text>
            <Textarea
              label={t("queue.auditNote")}
              placeholder={t("queue.auditPlaceholder")}
              value={manualCloseNote}
              onChange={(e) => setManualCloseNote(e.currentTarget.value)}
              minRows={2}
              maxLength={1000}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setManualCloseIntentId(null)} disabled={manualCloseMut.isPending}>
                {t("queue.cancel")}
              </Button>
              <Button
                color="orange"
                loading={manualCloseMut.isPending}
                disabled={!manualCloseIntentId}
                onClick={() => {
                  if (manualCloseIntentId) {
                    manualCloseMut.mutate({ intentId: manualCloseIntentId, note: manualCloseNote });
                  }
                }}
              >
                {t("queue.closeIntent")}
              </Button>
            </Group>
          </Stack>
        </Modal>

        <Paper p={0} radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("queue.colIntent")}</Table.Th>
                <Table.Th>{t("queue.colStatus")}</Table.Th>
                <Table.Th>{t("queue.colEmail")}</Table.Th>
                <Table.Th>{t("queue.colOrg")}</Table.Th>
                <Table.Th>{t("queue.colError")}</Table.Th>
                <Table.Th>{t("queue.colPaid")}</Table.Th>
                <Table.Th>{t("queue.colRevoke")}</Table.Th>
                <Table.Th>{t("queue.colAttempts")}</Table.Th>
                <Table.Th>{t("queue.colDlq")}</Table.Th>
                <Table.Th>{t("queue.colActions")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={10}>
                    <Text size="sm" c="dimmed" py="md" ta="center">
                      {queueQ.isFetching ? t("dashboard.loading") : t("queue.empty")}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                rows.map((row) => (
                  <Table.Tr key={row.intent_id}>
                    <Table.Td>
                      <ShortUuidCell id={row.intent_id} label="intent id" />
                    </Table.Td>
                    <Table.Td>{row.status}</Table.Td>
                    <Table.Td>{row.email ?? "—"}</Table.Td>
                    <Table.Td>
                      <ShortUuidCell id={row.organization_id} label="organization id" />
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" lineClamp={3} maw={220}>
                        {row.provision_last_error ?? "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{row.paid_at ?? "—"}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{row.billing_revoked_at ?? "—"}</Text>
                    </Table.Td>
                    <Table.Td>{row.provision_retry_count}</Table.Td>
                    <Table.Td>{row.provision_dead_letter ? t("queue.yes") : t("queue.no")}</Table.Td>
                    <Table.Td>
                      <Group gap={6} wrap="nowrap">
                        <Button
                          size="xs"
                          variant="outline"
                          disabled={!token.trim() || retryMut.isPending || manualCloseMut.isPending}
                          onClick={() => retryMut.mutate(row.intent_id)}
                        >
                          Retry
                        </Button>
                        <Button
                          size="xs"
                          variant="light"
                          color="orange"
                          disabled={
                            !token.trim() ||
                            manualCloseMut.isPending ||
                            retryMut.isPending ||
                            !["provision_failed", "dead_letter"].includes(row.status)
                          }
                          onClick={() => {
                            setManualCloseIntentId(row.intent_id);
                            setManualCloseNote("");
                          }}
                        >
                          {t("queue.close")}
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      </Stack>
    </Container>
  );
}
