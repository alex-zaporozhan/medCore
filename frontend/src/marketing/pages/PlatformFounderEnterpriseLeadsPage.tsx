import { API_BASE } from "@/api/client";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import { FounderQueryError, formatPlatformFounderApiError, founderFailMessage, parseJsonArray } from "@/marketing/platformFounderApi";
import { ROUTE_PATHS } from "@/routePaths";
import {
  ActionIcon,
  Box,
  Button,
  Container,
  Group,
  Menu,
  ScrollArea,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconDotsVertical } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

type LeadRow = {
  id: string;
  name: string;
  company_name: string;
  phone_or_email: string;
  status: string;
  lead_source: string;
  created_at: string;
};

export default function PlatformFounderEnterpriseLeadsPage() {
  const { t, i18n } = useTranslation("founder");
  const { token, setToken } = usePlatformFounderSession();
  const queryClient = useQueryClient();
  const [manualToken, setManualToken] = useState("");
  const [tokenVisible, setTokenVisible] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);

  const listQ = useQuery({
    queryKey: ["platform-founder", "enterprise-leads", token],
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/enterprise-leads`, {
        headers: { Authorization: `Bearer ${token.trim()}` },
      });
      if (r.status === 401) throw new FounderQueryError("session");
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      const raw: unknown = await r.json();
      return parseJsonArray<LeadRow>(raw);
    },
    enabled: Boolean(token.trim()),
  });

  const patchM = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/enterprise-leads/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token.trim()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status }),
      });
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      return r.json() as Promise<LeadRow>;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["platform-founder", "enterprise-leads", token] });
    },
  });

  const downloadCsv = async () => {
    setExportBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/platform/internal/enterprise-leads/export`, {
        headers: { Authorization: `Bearer ${token.trim()}` },
      });
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "enterprise_leads.csv";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportBusy(false);
    }
  };

  return (
    <Box style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Box px="md" py="sm" style={{ flex: "0 0 auto", borderBottom: "1px solid var(--divider)" }}>
        <Container size="xl" px={0}>
          <Stack gap="xs">
            <Title order={3}>{t("leads.title")}</Title>
            <Group align="flex-end" wrap="wrap" gap="sm">
              <TextInput
                label={t("leads.tokenLabel")}
                placeholder={t("leads.tokenPlaceholder")}
                type={tokenVisible ? "text" : "password"}
                value={manualToken}
                onChange={(e) => setManualToken(e.currentTarget.value)}
                style={{ flex: "1 1 280px", minWidth: 200 }}
              />
              <Button
                size="xs"
                variant="default"
                onClick={() => setTokenVisible((v) => !v)}
              >
                {tokenVisible ? t("leads.hide") : t("leads.show")}
              </Button>
              <Button
                size="xs"
                onClick={() => {
                  const v = manualToken.trim();
                  if (v) setToken(v);
                }}
              >
                {t("leads.applyToken")}
              </Button>
              <Button size="xs" variant="light" component={Link} to={ROUTE_PATHS.platform.dashboard}>
                {t("leads.toOverview")}
              </Button>
              <Button
                size="xs"
                variant="outline"
                loading={exportBusy}
                disabled={!token.trim()}
                onClick={() => void downloadCsv()}
              >
                {t("leads.downloadCsv")}
              </Button>
            </Group>
          </Stack>
        </Container>
      </Box>

      <ScrollArea style={{ flex: 1 }} type="scroll" offsetScrollbars>
        <Container size="xl" py="md" px="md">
          {listQ.isLoading ? (
            <Text size="sm" c="dimmed">
              {t("leads.loading")}
            </Text>
          ) : null}
          {listQ.error ? (
            <Text size="sm" c="red">
              {founderFailMessage(listQ.error, t)}
            </Text>
          ) : null}
          {listQ.data && listQ.data.length === 0 ? (
            <Text size="sm" c="dimmed">
              {t("leads.empty")}
            </Text>
          ) : null}
          {patchM.isError ? (
            <Text size="sm" c="red">
              {founderFailMessage(patchM.error, t)}
            </Text>
          ) : null}
          {listQ.data && listQ.data.length > 0 ? (
            <Table striped highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("leads.colCreated")}</Table.Th>
                  <Table.Th>{t("leads.colSource")}</Table.Th>
                  <Table.Th>{t("leads.colName")}</Table.Th>
                  <Table.Th>{t("leads.colCompany")}</Table.Th>
                  <Table.Th>{t("leads.colContact")}</Table.Th>
                  <Table.Th>{t("leads.colStatus")}</Table.Th>
                  <Table.Th w={56} />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {listQ.data.map((row) => (
                  <Table.Tr key={row.id}>
                    <Table.Td>
                      <Text size="xs">{new Date(row.created_at).toLocaleString(i18n.language.startsWith("ru") ? "ru-RU" : "en-US")}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{row.lead_source === "corporate" ? t("leads.sourceCorporate") : row.lead_source === "sandbox_demo" ? t("leads.sourceSandbox") : row.lead_source}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{row.name}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{row.company_name}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{row.phone_or_email}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{row.status === "NEW" ? t("leads.statusNew") : row.status === "IN_PROGRESS" ? t("leads.statusInProgress") : row.status === "CLOSED" ? t("leads.statusClosed") : row.status}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Menu shadow="md" width={200} position="bottom-end">
                        <Menu.Target>
                          <ActionIcon variant="subtle" aria-label={t("leads.actions")}>
                            <IconDotsVertical size={18} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item
                            disabled={row.status === "NEW" || patchM.isPending}
                            onClick={() => patchM.mutate({ id: row.id, status: "NEW" })}
                          >
                            {t("leads.statusNew")}
                          </Menu.Item>
                          <Menu.Item
                            disabled={row.status === "IN_PROGRESS" || patchM.isPending}
                            onClick={() => patchM.mutate({ id: row.id, status: "IN_PROGRESS" })}
                          >
                            {t("leads.statusInProgress")}
                          </Menu.Item>
                          <Menu.Item
                            disabled={row.status === "CLOSED" || patchM.isPending}
                            onClick={() => patchM.mutate({ id: row.id, status: "CLOSED" })}
                          >
                            {t("leads.statusClosed")}
                          </Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : null}
        </Container>
      </ScrollArea>
    </Box>
  );
}
