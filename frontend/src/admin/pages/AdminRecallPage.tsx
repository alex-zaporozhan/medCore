import {
  useAdminRecallSegments,
  useCreateRecallSegment,
  useUpdateRecallSegment,
  useDeleteRecallSegment,
  useAdminRecallTemplates,
  useCreateRecallTemplate,
  useUpdateRecallTemplate,
  useDeleteRecallTemplate,
  useAdminRecallCampaigns,
  useCreateRecallCampaign,
  useDeleteRecallCampaign,
  useRunRecallCampaign,
  useAdminRecallAutomations,
  useCreateRecallAutomation,
  useUpdateRecallAutomation,
  useDeleteRecallAutomation,
  type RecallSegmentWithCount,
  type RecallTemplateRead,
  type RecallAutomationRead,
} from "@/hooks/useAdminRecall";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Badge,
  Button,
  Group,
  Drawer,
  Select,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";

const TRIGGER_TYPES = [
  { value: "days_after_visit", label: "Через N дней после визита" },
];

function SegmentsTab({ clinicId }: { clinicId: string }) {
  const { data: segments, isLoading, isError, error } = useAdminRecallSegments(clinicId);
  const createMut = useCreateRecallSegment(clinicId);
  const updateMut = useUpdateRecallSegment(clinicId);
  const deleteMut = useDeleteRecallSegment(clinicId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editing, setEditing] = useState<RecallSegmentWithCount | null>(null);
  const [name, setName] = useState("");
  const [filterDays, setFilterDays] = useState<string>("");

  const reset = () => {
    setEditing(null);
    setName("");
    setFilterDays("");
  };

  const handleSave = () => {
    const filter_json =
      filterDays && Number(filterDays) > 0
        ? { last_visit_older_than_days: Number(filterDays) }
        : undefined;
    if (editing) {
      updateMut.mutate(
        { segmentId: editing.id, body: { name, filter_json } },
        { onSuccess: () => { close(); reset(); } }
      );
    } else {
      createMut.mutate(
        { name, filter_json },
        { onSuccess: () => { close(); reset(); } }
      );
    }
  };

  if (isLoading) return <PageSkeleton variant="table" rows={5} />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = segments ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Сегменты — превью количества пациентов</Text>
        <Button size="xs" onClick={() => { reset(); open(); }}>Добавить сегмент</Button>
      </Group>
      {list.length === 0 ? (
        <EmptyStateHint title="Нет сегментов. Создайте сегмент для рассылок." />
      ) : (
        <Table withTableBorder withColumnBorders verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Фильтр</Table.Th>
              <Table.Th>Пациентов</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>{s.name}</Table.Td>
                <Table.Td>
                  {(s.filter_json as { last_visit_older_than_days?: number } | null)?.last_visit_older_than_days != null
                    ? `Визит > ${(s.filter_json as { last_visit_older_than_days: number }).last_visit_older_than_days} дн. назад`
                    : "Все пациенты"}
                </Table.Td>
                <Table.Td>{s.patient_count}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setEditing(s);
                        setName(s.name);
                        setFilterDays(
                          (s.filter_json as { last_visit_older_than_days?: number } | null)?.last_visit_older_than_days != null
                            ? String((s.filter_json as { last_visit_older_than_days: number }).last_visit_older_than_days)
                            : ""
                        );
                        open();
                      }}
                    >
                      Изменить
                    </Button>
                    <Button
                      size="xs"
                      variant="subtle"
                      color="red"
                      onClick={() => deleteMut.mutate(s.id)}
                    >
                      Удалить
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Drawer position="right" size="md" opened={opened} onClose={() => { close(); reset(); }} title={editing ? "Изменить сегмент" : "Новый сегмент"}>
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.target.value)} />
          <TextInput
            label="Визит старше (дней), пусто = все"
            placeholder="90"
            value={filterDays}
            onChange={(e) => setFilterDays(e.target.value)}
          />
          <Button onClick={handleSave} loading={createMut.isPending || updateMut.isPending}>
            {editing ? "Сохранить" : "Создать"}
          </Button>
        </Stack>
      </Drawer>
    </Stack>
  );
}

function TemplatesTab({ clinicId }: { clinicId: string }) {
  const { data: templates, isLoading, isError, error } = useAdminRecallTemplates(clinicId);
  const createMut = useCreateRecallTemplate(clinicId);
  const updateMut = useUpdateRecallTemplate(clinicId);
  const deleteMut = useDeleteRecallTemplate(clinicId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editing, setEditing] = useState<RecallTemplateRead | null>(null);
  const [name, setName] = useState("");
  const [channel, setChannel] = useState("sms");
  const [subject, setSubject] = useState("");
  const [body_template, setBodyTemplate] = useState("");

  const reset = () => {
    setEditing(null);
    setName("");
    setChannel("sms");
    setSubject("");
    setBodyTemplate("");
  };

  const handleSave = () => {
    if (editing) {
      updateMut.mutate(
        {
          templateId: editing.id,
          body: { name, channel, subject: subject || null, body_template },
        },
        { onSuccess: () => { close(); reset(); } }
      );
    } else {
      createMut.mutate(
        { name, channel, subject: subject || null, body_template },
        { onSuccess: () => { close(); reset(); } }
      );
    }
  };

  if (isLoading) return <PageSkeleton variant="table" rows={5} />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = templates ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Шаблоны сообщений по каналам</Text>
        <Button size="xs" onClick={() => { reset(); open(); }}>Добавить шаблон</Button>
      </Group>
      {list.length === 0 ? (
        <EmptyStateHint title="Нет шаблонов. Создайте шаблон для кампаний." />
      ) : (
        <Table withTableBorder withColumnBorders verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Канал</Table.Th>
              <Table.Th>Текст (начало)</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((t) => (
              <Table.Tr key={t.id}>
                <Table.Td>{t.name}</Table.Td>
                <Table.Td>{t.channel}</Table.Td>
                <Table.Td>{t.body_template.slice(0, 50)}…</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setEditing(t);
                        setName(t.name);
                        setChannel(t.channel);
                        setSubject(t.subject ?? "");
                        setBodyTemplate(t.body_template);
                        open();
                      }}
                    >
                      Изменить
                    </Button>
                    <Button size="xs" variant="subtle" color="red" onClick={() => deleteMut.mutate(t.id)}>Удалить</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Drawer position="right" size="md" opened={opened} onClose={() => { close(); reset(); }} title={editing ? "Изменить шаблон" : "Новый шаблон"}>
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.target.value)} />
          <TextInput
            label="Канал"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            placeholder="sms / telegram / email"
          />
          <TextInput label="Тема (email)" value={subject} onChange={(e) => setSubject(e.target.value)} />
          <Textarea
            label="Текст шаблона ({{patient_id}} — подстановка)"
            value={body_template}
            onChange={(e) => setBodyTemplate(e.target.value)}
            minRows={3}
          />
          <Button onClick={handleSave} loading={createMut.isPending || updateMut.isPending}>
            {editing ? "Сохранить" : "Создать"}
          </Button>
        </Stack>
      </Drawer>
    </Stack>
  );
}

function CampaignsTab({ clinicId }: { clinicId: string }) {
  const { data: campaigns, isLoading, isError, error } = useAdminRecallCampaigns(clinicId);
  const { data: segments } = useAdminRecallSegments(clinicId);
  const { data: templates } = useAdminRecallTemplates(clinicId);
  const createMut = useCreateRecallCampaign(clinicId);
  const deleteMut = useDeleteRecallCampaign(clinicId);
  const runMut = useRunRecallCampaign(clinicId);
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");
  const [segmentId, setSegmentId] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);

  const reset = () => {
    setName("");
    setSegmentId(null);
    setTemplateId(null);
  };

  const handleCreate = () => {
    if (!segmentId || !templateId) return;
    createMut.mutate(
      { segment_id: segmentId, template_id: templateId, name: name || "Кампания", status: "draft" },
      { onSuccess: () => { close(); reset(); } }
    );
  };

  if (isLoading) return <PageSkeleton variant="table" rows={5} />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = campaigns ?? [];
  const segmentOptions = segments?.map((s) => ({ value: s.id, label: `${s.name} (${s.patient_count})` })) ?? [];
  const templateOptions = templates?.map((t) => ({ value: t.id, label: t.name })) ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Ручные кампании по сегментам</Text>
        <Button size="xs" onClick={() => { reset(); open(); }}>Создать кампанию</Button>
      </Group>
      {list.length === 0 ? (
        <EmptyStateHint title="Нет кампаний. Создайте кампанию и запустите рассылку." />
      ) : (
        <Table withTableBorder withColumnBorders verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Запущена / Завершена</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td>{c.name}</Table.Td>
                <Table.Td>
                  <Badge color={c.status === "completed" ? "green" : c.status === "running" ? "blue" : "gray"}>
                    {c.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {c.started_at ? new Date(c.started_at).toLocaleString() : "—"} /{" "}
                  {c.completed_at ? new Date(c.completed_at).toLocaleString() : "—"}
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {c.status === "draft" && (
                      <Button
                        size="xs"
                        onClick={() => runMut.mutate(c.id)}
                        loading={runMut.isPending}
                      >
                        Запустить
                      </Button>
                    )}
                    <Button size="xs" variant="subtle" color="red" onClick={() => deleteMut.mutate(c.id)}>Удалить</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Drawer position="right" size="md" opened={opened} onClose={() => { close(); reset(); }} title="Новая кампания">
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.target.value)} placeholder="Кампания" />
          <Select
            label="Сегмент"
            placeholder="Выберите сегмент"
            value={segmentId}
            onChange={setSegmentId}
            data={segmentOptions}
          />
          <Select
            label="Шаблон"
            placeholder="Выберите шаблон"
            value={templateId}
            onChange={setTemplateId}
            data={templateOptions}
          />
          <Button onClick={handleCreate} loading={createMut.isPending} disabled={!segmentId || !templateId}>
            Создать
          </Button>
        </Stack>
      </Drawer>
    </Stack>
  );
}

function AutomationsTab({ clinicId }: { clinicId: string }) {
  const { data: automations, isLoading, isError, error } = useAdminRecallAutomations(clinicId);
  const { data: templates } = useAdminRecallTemplates(clinicId);
  const createMut = useCreateRecallAutomation(clinicId);
  const updateMut = useUpdateRecallAutomation(clinicId);
  const deleteMut = useDeleteRecallAutomation(clinicId);
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState("days_after_visit");
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [enabled, setEnabled] = useState(true);

  const reset = () => {
    setName("");
    setTriggerType("days_after_visit");
    setTemplateId(null);
    setEnabled(true);
  };

  const handleCreate = () => {
    if (!templateId) return;
    createMut.mutate(
      {
        name: name || "Автоматизация",
        trigger_type: triggerType,
        template_id: templateId,
        enabled,
      },
      { onSuccess: () => { close(); reset(); } }
    );
  };

  const toggleEnabled = (a: RecallAutomationRead) => {
    updateMut.mutate({
      automationId: a.id,
      body: { enabled: !a.enabled },
    });
  };

  if (isLoading) return <PageSkeleton variant="table" rows={5} />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = automations ?? [];
  const templateOptions = templates?.map((t) => ({ value: t.id, label: t.name })) ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Триггерные автоматизации (вкл/выкл)</Text>
        <Button size="xs" onClick={() => { reset(); open(); }}>Добавить автоматизацию</Button>
      </Group>
      {list.length === 0 ? (
        <EmptyStateHint title="Нет автоматизаций. Создайте триггерную рассылку." />
      ) : (
        <Table withTableBorder withColumnBorders verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Триггер</Table.Th>
              <Table.Th>Включена</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((a) => (
              <Table.Tr key={a.id}>
                <Table.Td>{a.name}</Table.Td>
                <Table.Td>{a.trigger_type}</Table.Td>
                <Table.Td>
                  <Switch
                    checked={a.enabled}
                    onChange={() => toggleEnabled(a)}
                    disabled={updateMut.isPending}
                  />
                </Table.Td>
                <Table.Td>
                  <Button size="xs" variant="subtle" color="red" onClick={() => deleteMut.mutate(a.id)}>Удалить</Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Drawer position="right" size="md" opened={opened} onClose={() => { close(); reset(); }} title="Новая автоматизация">
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.target.value)} placeholder="Автоматизация" />
          <Select
            label="Тип триггера"
            value={triggerType}
            onChange={(v) => setTriggerType(v ?? "days_after_visit")}
            data={TRIGGER_TYPES}
          />
          <Select
            label="Шаблон"
            placeholder="Выберите шаблон"
            value={templateId}
            onChange={setTemplateId}
            data={templateOptions}
          />
          <Switch label="Включена" checked={enabled} onChange={(e) => setEnabled(e.currentTarget.checked)} />
          <Button onClick={handleCreate} loading={createMut.isPending} disabled={!templateId}>
            Создать
          </Button>
        </Stack>
      </Drawer>
    </Stack>
  );
}

export default function AdminRecallPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Recall / Автоматизации" />
        <Text size="sm" c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Recall / Автоматизации" />
      <Tabs defaultValue="segments">
        <Tabs.List>
          <Tabs.Tab value="segments">Сегменты</Tabs.Tab>
          <Tabs.Tab value="templates">Шаблоны</Tabs.Tab>
          <Tabs.Tab value="campaigns">Кампании</Tabs.Tab>
          <Tabs.Tab value="automations">Автоматизации</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="segments" pt="md">
          <SegmentsTab clinicId={clinicId} />
        </Tabs.Panel>
        <Tabs.Panel value="templates" pt="md">
          <TemplatesTab clinicId={clinicId} />
        </Tabs.Panel>
        <Tabs.Panel value="campaigns" pt="md">
          <CampaignsTab clinicId={clinicId} />
        </Tabs.Panel>
        <Tabs.Panel value="automations" pt="md">
          <AutomationsTab clinicId={clinicId} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
