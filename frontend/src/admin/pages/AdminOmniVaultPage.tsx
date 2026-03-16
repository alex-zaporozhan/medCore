/**
 * Omni-Vault — Фаза 5: медиа-галерея, Data Export Builder (Smart Presets), Full Backup.
 */

import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyState } from "@/shared/ui/EmptyState";
import {
  Button,
  Card,
  Drawer,
  Grid,
  Group,
  MultiSelect,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { getAdminToken } from "@/api/client";
import { useState } from "react";
import { IconPhoto, IconFileExport, IconCloudUpload, IconDownload, IconMessageCircle } from "@tabler/icons-react";

const EXPORT_PRESETS = [
  { id: "tax", label: "Для налоговой", columns: ["date", "patient", "service", "amount", "payment_type"] },
  { id: "vip_sleep", label: "Спящие VIP-клиенты", columns: ["patient", "ltv", "last_visit", "segment"] },
  { id: "consumables", label: "Расходники за период", columns: ["date", "service", "product", "amount", "warehouse"] },
];

function useMediaGallery(clinicId: string | null, filters: { type?: string; date_from?: string } = {}) {
  const token = getAdminToken();
  return useQuery({
    queryKey: ["admin", "omni-vault", "media", clinicId ?? "", filters],
    queryFn: async () => {
      if (!clinicId) return { items: [] };
      try {
        const params = new URLSearchParams();
        if (filters.type) params.set("type", filters.type);
        if (filters.date_from) params.set("date_from", filters.date_from);
        const res = await api.get<{ items: { id: string; url: string; type: string; patient_name?: string; channel?: string; created_at?: string }[] }>(
          `/v1/admin/clinics/${clinicId}/media?${params}`,
          token
        );
        return res ?? { items: [] };
      } catch {
        return { items: [] };
      }
    },
    enabled: !!token && !!clinicId,
  });
}

function useExportPresets(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: ["admin", "omni-vault", "export-presets", clinicId ?? ""],
    queryFn: async () => {
      if (!clinicId) return EXPORT_PRESETS;
      try {
        const res = await api.get<typeof EXPORT_PRESETS>(`/v1/admin/clinics/${clinicId}/export/presets`, token);
        return Array.isArray(res) && res.length > 0 ? res : EXPORT_PRESETS;
      } catch {
        return EXPORT_PRESETS;
      }
    },
    enabled: !!token && !!clinicId,
  });
}

function useRequestBackup(clinicId: string | null) {
  const token = getAdminToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post<{ task_id: string }>(
        `/v1/admin/clinics/${clinicId}/backup/request`,
        {},
        token
      );
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "omni-vault", "backup"] });
    },
  });
}

function useBackupStatus(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: ["admin", "omni-vault", "backup", clinicId ?? ""],
    queryFn: async () => {
      if (!clinicId) return null;
      try {
        return await api.get<{ task_id: string; status: string; download_url?: string }>(
          `/v1/admin/clinics/${clinicId}/backup/status`,
          token
        );
      } catch {
        return null;
      }
    },
    enabled: !!token && !!clinicId,
  });
}

type MediaItem = { id: string; url: string; type: string; patient_name?: string; channel?: string; created_at?: string };

export default function AdminOmniVaultPage() {
  const { currentClinicId } = useAdminClinic();
  const [mediaType, setMediaType] = useState<string | null>(null);
  const [exportColumns, setExportColumns] = useState<string[]>([]);
  const [exportEntity, setExportEntity] = useState<string>("patients");
  const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null);

  const { data: mediaData, isLoading: mediaLoading } = useMediaGallery(currentClinicId ?? null, {
    type: mediaType ?? undefined,
    date_from: new Date().toISOString().slice(0, 10),
  });
  const { data: presets } = useExportPresets(currentClinicId ?? null);
  const requestBackup = useRequestBackup(currentClinicId ?? null);
  const { data: backupStatus } = useBackupStatus(currentClinicId ?? null);

  const applyPreset = (preset: (typeof EXPORT_PRESETS)[0]) => {
    setExportColumns(preset.columns);
  };

  const handleExportExcel = () => {
    if (exportColumns.length === 0) return;
    // TODO: POST /admin/clinics/{id}/export с columns, entity → Excel; при ответе показать "Строк: N"
  };
  const handleExportCsv = () => {
    if (exportColumns.length === 0) return;
    // TODO: POST /admin/clinics/{id}/export с columns, entity → CSV
  };

  return (
    <Stack gap="lg">
      <ContextBar title="Omni-Vault (медиа и экспорт)" />

      <Tabs defaultValue="media">
        <Tabs.List>
          <Tabs.Tab value="media" leftSection={<IconPhoto size={16} />}>
            Медиа-галерея
          </Tabs.Tab>
          <Tabs.Tab value="voice" leftSection={<IconMessageCircle size={16} />}>
            Голосовые
          </Tabs.Tab>
          <Tabs.Tab value="export" leftSection={<IconFileExport size={16} />}>
            Export Builder
          </Tabs.Tab>
          <Tabs.Tab value="backup" leftSection={<IconCloudUpload size={16} />}>
            Full Backup
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="media" pt="md">
          <Group mb="md">
            <Text size="sm" fw={500}>
              Тип:
            </Text>
            <Button variant={mediaType === null ? "filled" : "light"} size="xs" onClick={() => setMediaType(null)}>
              Все
            </Button>
            <Button variant={mediaType === "xray" ? "filled" : "light"} size="xs" onClick={() => setMediaType("xray")}>
              Рентген
            </Button>
            <Button variant={mediaType === "video" ? "filled" : "light"} size="xs" onClick={() => setMediaType("video")}>
              Видео
            </Button>
          </Group>
          {mediaLoading ? (
            <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="md">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Skeleton key={i} height={140} radius="md" />
              ))}
            </SimpleGrid>
          ) : !mediaData?.items?.length ? (
            <EmptyState
              title="Нет медиафайлов"
              description="Загруженные файлы (рентген, фото, видео) появятся здесь. Фильтры по типу и дате."
            />
          ) : (
            <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="md">
              {mediaData.items.map((item) => (
                <Card
                  key={item.id}
                  withBorder
                  padding="xs"
                  radius="md"
                  style={{ cursor: "pointer", aspectRatio: "1", position: "relative" }}
                  onClick={() => setSelectedMedia(item)}
                >
                  <div style={{ width: "100%", height: 100, background: "var(--mantine-color-gray-2)", borderRadius: 4 }} />
                  {/* Overlay при наведении: аватар клиента, иконка канала, дата (Фаза 5) */}
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      borderRadius: 4,
                      background: "rgba(0,0,0,0.5)",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 4,
                      opacity: 0,
                      transition: "opacity 0.15s",
                    }}
                    className="media-card-overlay"
                    onMouseEnter={(e) => {
                      e.currentTarget.style.opacity = "1";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.opacity = "0";
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: "var(--mantine-color-gray-5)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "white",
                        fontSize: 12,
                      }}
                    >
                      {(item.patient_name ?? "—").slice(0, 1).toUpperCase()}
                    </div>
                    <Text size="xs" c="white">
                      {item.channel === "whatsapp" ? "WA" : item.channel === "telegram" ? "TG" : item.channel ?? "—"}
                    </Text>
                    <Text size="xs" c="gray.3">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}
                    </Text>
                  </div>
                  <Group gap="xs" mt="xs" wrap="nowrap">
                    <Text size="xs" c="dimmed" truncate>
                      {item.patient_name ?? "—"}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {item.channel ?? ""}
                    </Text>
                  </Group>
                  <Text size="xs" c="dimmed">
                    {item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}
                  </Text>
                </Card>
              ))}
            </SimpleGrid>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="voice" pt="md">
          <EmptyState
            title="Голосовые сообщения"
            description="Голосовые сообщения и транскрипты (waveform + авто-расшифровка) появятся здесь при наличии API."
          />
        </Tabs.Panel>

        <Tabs.Panel value="export" pt="md">
          <Grid>
            <Grid.Col span={{ base: 12, md: 5 }}>
              <Title order={6} mb="xs">
                Smart Presets
              </Title>
              <Stack gap="xs">
                {(presets ?? EXPORT_PRESETS).map((p) => (
                  <Button key={p.id} variant="light" size="sm" onClick={() => applyPreset(p)}>
                    {p.label}
                  </Button>
                ))}
              </Stack>
              <Title order={6} mt="md" mb="xs">
                Колонки
              </Title>
              <MultiSelect
                placeholder="Выберите колонки"
                data={["date", "patient", "service", "amount", "payment_type", "ltv", "last_visit", "segment", "product", "warehouse"]}
                value={exportColumns}
                onChange={setExportColumns}
              />
              <TextInput
                label="Сущность"
                mt="sm"
                value={exportEntity}
                onChange={(e) => setExportEntity(e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Paper p="md" withBorder>
                <Text size="sm" c="dimmed" mb="xs">
                  Превью (выбрано колонок: {exportColumns.length})
                </Text>
                <Text size="xs" c="dimmed" mb="xs">
                  Таблица в реальном времени появится при выборе колонок и наличии API экспорта.
                </Text>
                <Text size="sm" fw={500} mb="md">
                  Выбрано колонок: {exportColumns.length}. Строк: по данным экспорта.
                </Text>
                <Group mt="md">
                  <Button
                    leftSection={<IconDownload size={16} />}
                    variant="light"
                    onClick={handleExportExcel}
                    disabled={exportColumns.length === 0}
                  >
                    Экспорт в Excel
                  </Button>
                  <Button
                    leftSection={<IconDownload size={16} />}
                    variant="light"
                    onClick={handleExportCsv}
                    disabled={exportColumns.length === 0}
                  >
                    Экспорт в CSV
                  </Button>
                </Group>
              </Paper>
            </Grid.Col>
          </Grid>
        </Tabs.Panel>

        <Tabs.Panel value="backup" pt="md">
          <Card withBorder padding="md">
            <Title order={6} mb="xs">
              Запросить бэкап
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              Полная выгрузка данных. По готовности ссылка придёт в Telegram (при настройке).
            </Text>
            {backupStatus?.status === "completed" && backupStatus.download_url ? (
              <Stack gap="xs">
                <Text size="sm">Бэкап готов.</Text>
                <Button component="a" href={backupStatus.download_url} target="_blank" rel="noopener noreferrer">
                  Скачать
                </Button>
              </Stack>
            ) : backupStatus?.status === "pending" || backupStatus?.status === "running" ? (
              <Text size="sm" c="dimmed">
                Создание бэкапа... (статус: {backupStatus.status})
              </Text>
            ) : (
              <Button
                loading={requestBackup.isPending}
                onClick={() => requestBackup.mutate()}
              >
                Запросить бэкап
              </Button>
            )}
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Drawer медиафайла: файл + контекст чата/визита (Фаза 5) */}
      <Drawer
        position="right"
        size="md"
        opened={!!selectedMedia}
        onClose={() => setSelectedMedia(null)}
        title={selectedMedia ? (selectedMedia.patient_name ?? "Медиафайл") : ""}
      >
        {selectedMedia && (
          <Stack gap="md">
            <div
              style={{
                width: "100%",
                minHeight: 200,
                background: "var(--mantine-color-gray-2)",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {selectedMedia.url ? (
                <img
                  src={selectedMedia.url}
                  alt=""
                  style={{ maxWidth: "100%", maxHeight: 300, objectFit: "contain" }}
                />
              ) : (
                <Text size="sm" c="dimmed">
                  Превью (тип: {selectedMedia.type})
                </Text>
              )}
            </div>
            <Group gap="xs">
              <Text size="sm" fw={500}>
                Пациент:
              </Text>
              <Text size="sm" c="dimmed">
                {selectedMedia.patient_name ?? "—"}
              </Text>
            </Group>
            <Group gap="xs">
              <Text size="sm" fw={500}>
                Канал:
              </Text>
              <Text size="sm" c="dimmed">
                {selectedMedia.channel ?? "—"}
              </Text>
            </Group>
            <Text size="xs" c="dimmed">
              Дата: {selectedMedia.created_at ? new Date(selectedMedia.created_at).toLocaleString() : "—"}
            </Text>
            <Button
              variant="light"
              size="sm"
              leftSection={<IconMessageCircle size={16} />}
              onClick={() => setSelectedMedia(null)}
            >
              Открыть в чате
            </Button>
          </Stack>
        )}
      </Drawer>
    </Stack>
  );
}
