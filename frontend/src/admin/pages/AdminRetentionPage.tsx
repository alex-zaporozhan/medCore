/**
 * Retention: сегменты аудитории, кампании recall, персональные офферы, воронка ROI.
 */

import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAdminRecallTemplates,
  useCreateRecallCampaign,
} from "@/hooks/useAdminRecall";
import {
  type RetentionOfferItem,
  useAdminRetentionCampaignsRoi,
  useAdminRetentionSegments,
  useGenerateRetentionOffers,
} from "@/hooks/useAdminRetention";
import { queryKeys } from "@/queryKeys";
import { ROUTE_PATHS } from "@/routePaths";
import {
  ADMIN_TABLE_PROPS,
  AdminDataTableSurface,
  AdminDataTableToolbar,
  AdminDrawer,
  ContextBar,
} from "@/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import {
  Badge,
  Button,
  Grid,
  Group,
  ScrollArea,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { IconChartFunnel, IconRobot, IconSend, IconUsers } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

export default function AdminRetentionPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const { data: segments, isLoading: segmentsLoading } = useAdminRetentionSegments(clinicId);
  const { data: campaignsRoi, isLoading: roiLoading } = useAdminRetentionCampaignsRoi(clinicId);
  const {
    data: recallTemplates,
    isLoading: templatesLoading,
    isError: templatesError,
  } = useAdminRecallTemplates(clinicId);
  const createCampaign = useCreateRecallCampaign(clinicId);
  const generateOffers = useGenerateRetentionOffers();

  const [campaignDrawerOpen, setCampaignDrawerOpen] = useState(false);
  const [campaignName, setCampaignName] = useState("");
  const [campaignSegmentId, setCampaignSegmentId] = useState<string | null>(null);
  const [campaignTemplateId, setCampaignTemplateId] = useState<string | null>(null);
  const [offersModalSegmentId, setOffersModalSegmentId] = useState<string | null>(null);
  const [offersResult, setOffersResult] = useState<RetentionOfferItem[] | null>(null);
  const [offersError, setOffersError] = useState<string | null>(null);

  useEffect(() => {
    if (!offersModalSegmentId) {
      setOffersResult(null);
      setOffersError(null);
      return;
    }
    setOffersResult(null);
    setOffersError(null);
  }, [offersModalSegmentId]);

  const segmentOptions = (segments ?? []).map((s) => ({ value: s.id, label: s.name }));
  const templateOptions =
    recallTemplates?.map((t) => ({ value: t.id, label: `${t.name} (${t.channel})` })) ?? [];

  const handleCreateCampaign = () => {
    if (!clinicId || !campaignName.trim() || !campaignSegmentId || !campaignTemplateId) return;
    createCampaign.mutate(
      {
        segment_id: campaignSegmentId,
        template_id: campaignTemplateId,
        name: campaignName.trim(),
      },
      {
        onSuccess: () => {
          setCampaignDrawerOpen(false);
          setCampaignName("");
          setCampaignSegmentId(null);
          setCampaignTemplateId(null);
          void qc.invalidateQueries({ queryKey: queryKeys.adminRetention.campaignsRoi(clinicId) });
          void qc.invalidateQueries({ queryKey: ["admin", "clinics", clinicId, "recall"] });
        },
      }
    );
  };

  const handleRequestOffers = () => {
    if (!offersModalSegmentId) return;
    setOffersError(null);
    generateOffers.mutate(offersModalSegmentId, {
      onSuccess: (rows) => setOffersResult(rows),
      onError: (err) =>
        setOffersError(err instanceof Error ? err.message : "Не удалось выполнить запрос"),
    });
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
          setCampaignTemplateId(null);
        }}
        title="Новая кампания"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Кампания создаётся в модуле напоминаний: нужны сегмент, шаблон сообщения и название.
          </Text>
          {templatesError ? (
            <Text size="sm" c="dimmed">
              Шаблоны недоступны: проверьте права на раздел «Напоминания» или обратитесь к администратору.
            </Text>
          ) : null}
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
          <Select
            label="Шаблон сообщения"
            placeholder={templatesLoading ? "Загрузка…" : "Выберите шаблон"}
            data={templateOptions}
            value={campaignTemplateId}
            onChange={setCampaignTemplateId}
            clearable
            disabled={templatesLoading || templateOptions.length === 0}
            description={
              templateOptions.length === 0 && !templatesLoading
                ? "Создайте шаблон в разделе «Напоминания»."
                : undefined
            }
          />
          {createCampaign.isError ? (
            <Text size="sm" c="red">
              {createCampaign.error instanceof Error
                ? createCampaign.error.message
                : "Не удалось создать кампанию"}
            </Text>
          ) : null}
          <Group justify="flex-end" mt="md">
            <Button variant="subtle" onClick={() => setCampaignDrawerOpen(false)}>
              Отмена
            </Button>
            <Button
              onClick={handleCreateCampaign}
              disabled={
                !campaignName.trim() ||
                !campaignSegmentId ||
                !campaignTemplateId ||
                createCampaign.isPending
              }
              loading={createCampaign.isPending}
              leftSection={<IconSend size={16} />}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>

      {offersModalSegmentId && (
        <AdminDrawer
          position="right"
          size="md"
          opened={!!offersModalSegmentId}
          onClose={() => setOffersModalSegmentId(null)}
          title="Персональные офферы по сегменту"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Сегмент «{segments?.find((s) => s.id === offersModalSegmentId)?.name ?? ""}». Запрос
              формирует черновики предложений на сервере; результат отобразится ниже.
            </Text>
            <Button
              variant="light"
              leftSection={<IconRobot size={16} />}
              onClick={handleRequestOffers}
              loading={generateOffers.isPending}
            >
              Запросить генерацию
            </Button>
            {offersError ? (
              <Text size="sm" c="red">
                {offersError}
              </Text>
            ) : null}
            {offersResult && offersResult.length === 0 ? (
              <Text size="sm" c="dimmed">
                Пока нет сгенерированных предложений для этого сегмента.
              </Text>
            ) : null}
            {offersResult && offersResult.length > 0 ? (
              <ScrollArea h={280}>
                <Stack gap="xs">
                  {offersResult.map((o) => (
                    <Text key={o.patient_id} size="sm">
                      <strong>{o.patient_id.slice(0, 8)}…</strong>: {o.offer_text}
                    </Text>
                  ))}
                </Stack>
              </ScrollArea>
            ) : null}
            <Button variant="subtle" onClick={() => setOffersModalSegmentId(null)}>
              Закрыть
            </Button>
          </Stack>
        </AdminDrawer>
      )}

      <Tabs defaultValue="segments">
        <Tabs.List>
          <Tabs.Tab value="segments" leftSection={<IconUsers size={16} />}>
            Сегменты
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
            <AdminDataTableSurface>
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
            </AdminDataTableSurface>
          ) : !segments?.length ? (
            <EmptyState
              title="Нет сегментов"
              description="Добавьте сегменты в разделе напоминаний — они же используются для удержания."
              action={{
                label: "Открыть напоминания",
                onClick: () => navigate(ROUTE_PATHS.admin.recall),
              }}
            />
          ) : (
            <Grid>
              {segments.map((seg) => (
                <Grid.Col key={seg.id} span={{ base: 12, sm: 6, md: 3 }}>
                  <AdminDataTableSurface>
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
                  </AdminDataTableSurface>
                </Grid.Col>
              ))}
            </Grid>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="waterfall" pt="md">
          <Stack gap="md">
            <AdminDataTableToolbar>
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
            </AdminDataTableToolbar>

            <Title order={5}>ROI кампаний (воронка до кассы)</Title>
            {roiLoading ? (
              <Text size="sm" c="dimmed">
                Загрузка...
              </Text>
            ) : !campaignsRoi?.length ? (
              <EmptyState
                title="Нет кампаний"
                description="Создайте кампанию, чтобы видеть воронку: Отправлено → Прочитано → Перешли → Записались → Оплатили в кассу."
                action={{
                  label: "Создать кампанию",
                  onClick: () => setCampaignDrawerOpen(true),
                }}
              />
            ) : (
              <Table withTableBorder {...ADMIN_TABLE_PROPS}>
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
