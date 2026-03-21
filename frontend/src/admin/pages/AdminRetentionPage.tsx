/**
 * Retention (Smart Retention Engine) — Фаза 5.
 * AI-сегменты, конструктор кампании, AI Hyper-Personalization,
 * омниканальный каскад Waterfall, ROI кампании (воронка до кассы).
 */

import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { AdminDrawer, ContextBar } from "@/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import {
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Paper,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import {
  useAdminRetentionSegments,
  useAdminRetentionCampaignsRoi,
} from "@/hooks/useAdminRetention";
import { IconUsers, IconSend, IconChartFunnel, IconRobot } from "@tabler/icons-react";
import { useState } from "react";

export default function AdminRetentionPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: segments, isLoading: segmentsLoading } = useAdminRetentionSegments(
    currentClinicId ?? null
  );
  const { data: campaignsRoi, isLoading: roiLoading } = useAdminRetentionCampaignsRoi(
    currentClinicId ?? null
  );
  const [campaignDrawerOpen, setCampaignDrawerOpen] = useState(false);
  const [campaignName, setCampaignName] = useState("");
  const [campaignSegmentId, setCampaignSegmentId] = useState<string | null>(null);
  const [offersModalSegmentId, setOffersModalSegmentId] = useState<string | null>(null);

  const segmentOptions = (segments ?? []).map((s) => ({ value: s.id, label: s.name }));
  const handleCreateCampaign = () => {
    if (!campaignName.trim() || !campaignSegmentId) return;
    setCampaignDrawerOpen(false);
    setCampaignName("");
    setCampaignSegmentId(null);
  };

  return (
    <Stack gap="lg">
      <ContextBar
        title="Retention (Smart Retention Engine)"
        actions={
          <Button leftSection={<IconSend size={16} />} onClick={() => setCampaignDrawerOpen(true)}>
            Создать кампанию
          </Button>
        }
      />

      {/* Конструктор кампании — Drawer (Фаза 5) */}
      <AdminDrawer
        position="right"
        size="md"
        opened={campaignDrawerOpen}
        onClose={() => {
          setCampaignDrawerOpen(false);
          setCampaignName("");
          setCampaignSegmentId(null);
        }}
        title="Новая кампания"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Каскад: WhatsApp → Push через 24ч → SMS для VIP. Сегмент определяет целевую аудиторию.
          </Text>
          <TextInput
            label="Название кампании"
            placeholder="Например: Возврат спящих VIP"
            value={campaignName}
            onChange={(e) => setCampaignName(e.currentTarget.value)}
          />
          <Select
            label="Сегмент"
            placeholder="Выберите сегмент"
            data={segmentOptions}
            value={campaignSegmentId}
            onChange={setCampaignSegmentId}
            clearable
          />
          <Group justify="flex-end" mt="md">
            <Button variant="subtle" onClick={() => setCampaignDrawerOpen(false)}>
              Отмена
            </Button>
            <Button
              onClick={handleCreateCampaign}
              disabled={!campaignName.trim() || !campaignSegmentId}
              leftSection={<IconSend size={16} />}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>

      {/* Модалка «Сгенерировать офферы» по сегменту (AI Hyper-Personalization) */}
      {offersModalSegmentId && (
        <AdminDrawer
          position="right"
          size="sm"
          opened={!!offersModalSegmentId}
          onClose={() => setOffersModalSegmentId(null)}
          title="AI офферы по сегменту"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Персональные офферы для сегмента «
              {segments?.find((s) => s.id === offersModalSegmentId)?.name ?? ""}» генерируются по
              API (POST retention/generate-offers). При отсутствии API — заглушка.
            </Text>
            <Button variant="light" leftSection={<IconRobot size={16} />}>
              Запросить генерацию
            </Button>
            <Button variant="subtle" onClick={() => setOffersModalSegmentId(null)}>
              Закрыть
            </Button>
          </Stack>
        </AdminDrawer>
      )}

      <Tabs defaultValue="segments">
        <Tabs.List>
          <Tabs.Tab value="segments" leftSection={<IconUsers size={16} />}>
            AI-сегменты
          </Tabs.Tab>
          <Tabs.Tab value="waterfall" leftSection={<IconChartFunnel size={16} />}>
            Waterfall и ROI
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="segments" pt="md">
          <Text size="sm" c="dimmed" mb="md">
            Когорты для персональных офферов. Каскад: WhatsApp → Push через 24ч → SMS для VIP.
          </Text>
          {segmentsLoading ? (
            <Paper p="md" withBorder>
              <Stack gap="xs">
                {[1, 2, 3, 4].map((i) => (
                  <Group key={i} gap="md">
                    <Badge variant="light" color="gray" size="lg">
                      —
                    </Badge>
                    <Text size="sm" c="dimmed">
                      Загрузка...
                    </Text>
                  </Group>
                ))}
              </Stack>
            </Paper>
          ) : !segments?.length ? (
            <EmptyState
              title="Нет сегментов"
              description="Сегменты появятся после настройки Retention и подключения API."
              action={{ label: "Настройки", onClick: () => {} }}
            />
          ) : (
            <Grid>
              {segments.map((seg) => (
                <Grid.Col key={seg.id} span={{ base: 12, sm: 6, md: 3 }}>
                  <Card withBorder padding="md" radius="md">
                    <Group justify="space-between" mb="xs">
                      <Text fw={600} size="sm">
                        {seg.name}
                      </Text>
                      <Badge size="sm" variant="light">
                        {seg.patient_count}
                      </Badge>
                    </Group>
                    {seg.description && (
                      <Text size="xs" c="dimmed" lineClamp={2}>
                        {seg.description}
                      </Text>
                    )}
                    <Button
                      size="xs"
                      variant="light"
                      mt="sm"
                      leftSection={<IconRobot size={14} />}
                      onClick={() => setOffersModalSegmentId(seg.id)}
                    >
                      Сгенерировать офферы
                    </Button>
                  </Card>
                </Grid.Col>
              ))}
            </Grid>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="waterfall" pt="md">
          <Stack gap="md">
            <Card withBorder padding="md">
              <Title order={5} mb="xs">
                Омниканальный каскад (Waterfall)
              </Title>
              <Group gap="lg">
                <Badge size="lg" color="green">
                  WhatsApp
                </Badge>
                <Text size="sm" c="dimmed">
                  →
                </Text>
                <Badge size="lg" color="blue">
                  Push через 24ч
                </Badge>
                <Text size="sm" c="dimmed">
                  →
                </Text>
                <Badge size="lg" color="violet">
                  SMS для VIP
                </Badge>
              </Group>
            </Card>

            <Title order={5}>ROI кампаний (воронка до кассы)</Title>
            {roiLoading ? (
              <Text size="sm" c="dimmed">
                Загрузка...
              </Text>
            ) : !campaignsRoi?.length ? (
              <EmptyState
                title="Нет кампаний"
                description="Создайте кампанию, чтобы видеть воронку: Отправлено → Прочитано → Перешли → Записались → Оплатили в кассу."
                action={{ label: "Создать кампанию", onClick: () => {} }}
              />
            ) : (
              <Table withTableBorder withColumnBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Кампания</Table.Th>
                    <Table.Th>Отправлено</Table.Th>
                    <Table.Th>Прочитано</Table.Th>
                    <Table.Th>Перешли</Table.Th>
                    <Table.Th>Записались</Table.Th>
                    <Table.Th>Оплатили в кассу</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {campaignsRoi.map((row) => (
                    <Table.Tr key={row.campaign_id}>
                      <Table.Td>{row.campaign_name}</Table.Td>
                      <Table.Td>{row.sent}</Table.Td>
                      <Table.Td>{row.read}</Table.Td>
                      <Table.Td>{row.clicked}</Table.Td>
                      <Table.Td>{row.booked}</Table.Td>
                      <Table.Td>{row.paid}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
