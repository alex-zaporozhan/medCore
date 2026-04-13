import { API_BASE } from "@/api/client";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import { formatPlatformFounderApiError, parseJsonArray } from "@/marketing/platformFounderApi";
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

const STATUS_LABEL: Record<string, string> = {
  NEW: "Новая",
  IN_PROGRESS: "В работе",
  CLOSED: "Закрыта",
};

const SOURCE_LABEL: Record<string, string> = {
  corporate: "Корпоратив",
  sandbox_demo: "Демо",
};

export default function PlatformFounderEnterpriseLeadsPage() {
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
      if (r.status === 401) throw new Error("Сессия истекла. Выйдите и войдите снова.");
      if (!r.ok) throw new Error(await formatPlatformFounderApiError(r, `Ошибка ${r.status}`));
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
      if (!r.ok) throw new Error(await formatPlatformFounderApiError(r, `Ошибка ${r.status}`));
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
      if (!r.ok) throw new Error(await formatPlatformFounderApiError(r, `Ошибка ${r.status}`));
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
            <Title order={3}>Заявки на корпоративное внедрение</Title>
            <Group align="flex-end" wrap="wrap" gap="sm">
              <TextInput
                label="Токен (ручная подмена)"
                placeholder="Bearer из входа"
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
                {tokenVisible ? "Скрыть" : "Показать"}
              </Button>
              <Button
                size="xs"
                onClick={() => {
                  const v = manualToken.trim();
                  if (v) setToken(v);
                }}
              >
                Применить токен
              </Button>
              <Button size="xs" variant="light" component={Link} to={ROUTE_PATHS.platform.dashboard}>
                К обзору
              </Button>
              <Button
                size="xs"
                variant="outline"
                loading={exportBusy}
                disabled={!token.trim()}
                onClick={() => void downloadCsv()}
              >
                Скачать CSV
              </Button>
            </Group>
          </Stack>
        </Container>
      </Box>

      <ScrollArea style={{ flex: 1 }} type="scroll" offsetScrollbars>
        <Container size="xl" py="md" px="md">
          {listQ.isLoading ? (
            <Text size="sm" c="dimmed">
              Загрузка…
            </Text>
          ) : null}
          {listQ.error ? (
            <Text size="sm" c="red">
              {listQ.error instanceof Error ? listQ.error.message : "Ошибка загрузки"}
            </Text>
          ) : null}
          {listQ.data && listQ.data.length === 0 ? (
            <Text size="sm" c="dimmed">
              Заявок пока нет.
            </Text>
          ) : null}
          {patchM.isError ? (
            <Text size="sm" c="red">
              {patchM.error instanceof Error ? patchM.error.message : "Не удалось обновить статус"}
            </Text>
          ) : null}
          {listQ.data && listQ.data.length > 0 ? (
            <Table striped highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Создана</Table.Th>
                  <Table.Th>Источник</Table.Th>
                  <Table.Th>Имя</Table.Th>
                  <Table.Th>Компания</Table.Th>
                  <Table.Th>Контакт</Table.Th>
                  <Table.Th>Статус</Table.Th>
                  <Table.Th w={56} />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {listQ.data.map((row) => (
                  <Table.Tr key={row.id}>
                    <Table.Td>
                      <Text size="xs">{new Date(row.created_at).toLocaleString("ru-RU")}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{SOURCE_LABEL[row.lead_source] ?? row.lead_source}</Text>
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
                      <Text size="sm">{STATUS_LABEL[row.status] ?? row.status}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Menu shadow="md" width={200} position="bottom-end">
                        <Menu.Target>
                          <ActionIcon variant="subtle" aria-label="Действия">
                            <IconDotsVertical size={18} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item
                            disabled={row.status === "NEW" || patchM.isPending}
                            onClick={() => patchM.mutate({ id: row.id, status: "NEW" })}
                          >
                            Новая
                          </Menu.Item>
                          <Menu.Item
                            disabled={row.status === "IN_PROGRESS" || patchM.isPending}
                            onClick={() => patchM.mutate({ id: row.id, status: "IN_PROGRESS" })}
                          >
                            В работе
                          </Menu.Item>
                          <Menu.Item
                            disabled={row.status === "CLOSED" || patchM.isPending}
                            onClick={() => patchM.mutate({ id: row.id, status: "CLOSED" })}
                          >
                            Закрыта
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
