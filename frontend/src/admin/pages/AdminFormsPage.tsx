import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  useAdminFormTemplates,
  useAdminFormSubmissions,
  useAdminFormSubmissionDetail,
  useUpsertAdminFormTemplate,
} from "@/hooks";
import type { DigitalFormSubmissionListItem, DigitalFormTemplate } from "@/api/types";
import { AdminDrawer, QueryErrorAlert } from "@/shared/ui";
import {
  ActionIcon,
  Box,
  Button,
  Group,
  JsonInput,
  Menu,
  Paper,
  SegmentedControl,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { IconDotsVertical } from "@tabler/icons-react";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
type Mode = "templates" | "submissions";

export default function AdminFormsPage() {
  const [mode, setMode] = useState<Mode>("templates");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<DigitalFormTemplate | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [requiresSignature, setRequiresSignature] = useState(false);
  const [requiredForVisit, setRequiredForVisit] = useState(false);
  const [active, setActive] = useState(true);
  const [schemaJson, setSchemaJson] = useState<string>('{"fields": []}');
  const [filterPatientId, setFilterPatientId] = useState("");
  const [filterBookingId, setFilterBookingId] = useState("");
  const [filterTemplateCode, setFilterTemplateCode] = useState("");
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const pid = searchParams.get("patient_id");
    if (pid) setFilterPatientId(pid);
  }, [searchParams]);

  const {
    data: templates,
    isLoading: templatesLoading,
    isError: templatesError,
    error: templatesQueryError,
  } = useAdminFormTemplates();
  const {
    data: submissions,
    isLoading: submissionsLoading,
    isError: submissionsError,
    error: submissionsQueryError,
  } = useAdminFormSubmissions({
      patient_id: filterPatientId.trim() || null,
      booking_id: filterBookingId.trim() || null,
      template_code: filterTemplateCode.trim() || null,
    });
  const { data: submissionDetail, isLoading: detailLoading } =
    useAdminFormSubmissionDetail(selectedSubmissionId);
  const upsertTemplate = useUpsertAdminFormTemplate();

  const openCreate = () => {
    setEditingTemplate(null);
    setCode("");
    setName("");
    setRequiresSignature(false);
    setRequiredForVisit(false);
    setActive(true);
    setSchemaJson(
      JSON.stringify(
        {
          fields: [
            {
              id: "full_name",
              label: "ФИО",
              type: "text",
              required: true,
              sensitive: true,
            },
          ],
        },
        null,
        2
      )
    );
    setEditorOpen(true);
  };

  const openEdit = (t: DigitalFormTemplate) => {
    setEditingTemplate(t);
    setCode(t.code);
    setName(t.name);
    setRequiresSignature(t.requires_signature);
    setRequiredForVisit(t.required_for_visit_completion ?? false);
    setActive(t.active);
    setSchemaJson(JSON.stringify(t.schema, null, 2));
    setEditorOpen(true);
  };

  const openDuplicate = (t: DigitalFormTemplate) => {
    setEditingTemplate(null);
    setCode(t.code + "_copy");
    setName(t.name + " (копия)");
    setRequiresSignature(t.requires_signature);
    setRequiredForVisit(t.required_for_visit_completion ?? false);
    setActive(false);
    setSchemaJson(JSON.stringify(t.schema, null, 2));
    setEditorOpen(true);
  };

  const handleSave = () => {
    let parsedSchema: unknown;
    try {
      parsedSchema = JSON.parse(schemaJson);
    } catch {
      alert("Некорректный JSON схемы");
      return;
    }
    if (!code.trim() || !name.trim()) {
      alert("Укажите код и название шаблона");
      return;
    }
    upsertTemplate.mutate(
      {
        id: editingTemplate?.id,
        body: {
          code: code.trim(),
          name: name.trim(),
          description: editingTemplate?.description ?? null,
          schema: parsedSchema as DigitalFormTemplate["schema"],
          requires_signature: requiresSignature,
          required_for_visit_completion: requiredForVisit,
          active,
        },
      },
      {
        onSuccess: () => {
          setEditorOpen(false);
        },
      }
    );
  };

  return (
    <Stack>
      <ContextBar
        title="Формы и документы"
        actions={
          <SegmentedControl
            value={mode}
            onChange={(v) => setMode(v as Mode)}
            data={[
              { value: "templates", label: "Шаблоны форм" },
              { value: "submissions", label: "Отправленные формы" },
            ]}
          />
        }
      />

      {mode === "templates" && (
        <Stack>
          <Group justify="space-between" mb="xs">
            <Text size="sm" c="dimmed">
              Управление цифровыми анкетами и согласиями. Активные шаблоны доступны в PWA и через ссылки.
            </Text>
            <Button size="xs" onClick={openCreate}>
              Новый шаблон
            </Button>
          </Group>
          {templatesLoading && <PageSkeleton variant="table" rows={5} />}
          {templatesError && (
            <QueryErrorAlert error={templatesQueryError} title="Не удалось загрузить шаблоны" />
          )}
          {!templatesLoading && !templatesError && !(templates?.length) && (
            <EmptyState
              title="Нет шаблонов форм"
              description="Создайте первый шаблон анкеты или согласия для отправки пациентам."
              action={{ label: "Создать шаблон", onClick: openCreate }}
            />
          )}
          {!templatesLoading && !templatesError && (templates?.length ?? 0) > 0 && (
            <Paper withBorder radius="md" p="sm">
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Код</Table.Th>
                    <Table.Th>Название</Table.Th>
                    <Table.Th>Версия</Table.Th>
                    <Table.Th>Подпись</Table.Th>
                    <Table.Th>К завершению визита</Table.Th>
                    <Table.Th>Активен</Table.Th>
                    <Table.Th style={{ width: 52 }} />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(templates ?? []).map((t) => (
                    <Table.Tr key={t.id}>
                      <Table.Td>{t.code}</Table.Td>
                      <Table.Td>{t.name}</Table.Td>
                      <Table.Td>{t.version}</Table.Td>
                      <Table.Td>{t.requires_signature ? "Да" : "Нет"}</Table.Td>
                      <Table.Td>{t.required_for_visit_completion ? "Да" : "Нет"}</Table.Td>
                      <Table.Td>{t.active ? "Да" : "Нет"}</Table.Td>
                      <Table.Td>
                        <Menu position="bottom-end" withArrow>
                          <Menu.Target>
                            <ActionIcon variant="subtle" size="sm">
                              <IconDotsVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item onClick={() => openEdit(t)}>
                              Редактировать
                            </Menu.Item>
                            <Menu.Item onClick={() => openDuplicate(t)}>
                              Дублировать
                            </Menu.Item>
                            <Menu.Item color="red" disabled title="Удаление шаблона (API пока не реализован)">
                              Удалить
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Stack>
      )}

      {mode === "submissions" && (
        <Stack>
          <Text size="sm" c="dimmed">
            История заполненных форм с привязкой к пациентам и визитам.
          </Text>
          <Group gap="xs">
            <TextInput
              placeholder="ID пациента (фильтр)"
              value={filterPatientId}
              onChange={(e) => setFilterPatientId(e.currentTarget.value)}
              size="xs"
              style={{ width: 200 }}
            />
            <TextInput
              placeholder="ID визита (фильтр)"
              value={filterBookingId}
              onChange={(e) => setFilterBookingId(e.currentTarget.value)}
              size="xs"
              style={{ width: 200 }}
            />
            <TextInput
              placeholder="Код шаблона (фильтр)"
              value={filterTemplateCode}
              onChange={(e) => setFilterTemplateCode(e.currentTarget.value)}
              size="xs"
              style={{ width: 180 }}
            />
          </Group>
          <Paper withBorder radius="md" p="sm">
            {submissionsLoading && <Text size="sm">Загрузка форм...</Text>}
            {submissionsError && (
              <QueryErrorAlert error={submissionsQueryError} title="Не удалось загрузить отправленные формы" />
            )}
            {!submissionsLoading && !submissionsError && (
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Дата</Table.Th>
                    <Table.Th>Статус</Table.Th>
                    <Table.Th>Шаблон</Table.Th>
                    <Table.Th>Пациент</Table.Th>
                    <Table.Th>Визит</Table.Th>
                    <Table.Th>Отправитель</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(submissions ?? []).map((s: DigitalFormSubmissionListItem) => (
                    <Table.Tr
                      key={s.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedSubmissionId(s.id)}
                    >
                      <Table.Td>
                        {s.submitted_at || s.signed_at || s.created_at
                          ? new Date(
                              s.submitted_at ?? s.signed_at ?? s.created_at ?? ""
                            ).toLocaleString()
                          : "—"}
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" tt="uppercase">
                          {s.status}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Stack gap={2}>
                          <Text size="sm" fw={500}>
                            {s.template_name || s.template_id}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {s.template_code}
                          </Text>
                        </Stack>
                      </Table.Td>
                      <Table.Td>{s.patient_id || "—"}</Table.Td>
                      <Table.Td>{s.booking_id || "—"}</Table.Td>
                      <Table.Td>{s.submitted_by}</Table.Td>
                      <Table.Td>
                        <Button size="xs" variant="light" onClick={(e) => { e.stopPropagation(); setSelectedSubmissionId(s.id); }}>
                          Детали
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {!submissions?.length && (
                    <Table.Tr>
                      <Table.Td colSpan={7}>
                        <Text size="sm" c="dimmed">
                          Заполненных форм пока нет.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            )}
          </Paper>
        </Stack>
      )}

      <AdminDrawer
        opened={!!selectedSubmissionId}
        onClose={() => setSelectedSubmissionId(null)}
        position="right"
        size="md"
        title="Детали формы"
      >
        {selectedSubmissionId && (
          <Stack gap="md">
            {detailLoading && <Text size="sm">Загрузка...</Text>}
            {submissionDetail && (
              <>
                <Stack gap={4}>
                  <Text size="sm" fw={600}>
                    {submissionDetail.template.name}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Код: {submissionDetail.template.code} · Статус: {submissionDetail.submission.status} ·{" "}
                    {submissionDetail.submission.submitted_at || submissionDetail.submission.signed_at
                      ? new Date(
                          submissionDetail.submission.submitted_at ??
                            submissionDetail.submission.signed_at ??
                            ""
                        ).toLocaleString()
                      : "—"}{" "}
                    · {submissionDetail.submission.submitted_by}
                  </Text>
                </Stack>
                <Stack gap="xs">
                  <Text size="sm" fw={500}>
                    Данные (чувствительные поля скрыты)
                  </Text>
                  {Object.entries(submissionDetail.submission.data).map(([key, value]) => (
                    <Group key={key} gap="xs">
                      <Text size="xs" c="dimmed" style={{ minWidth: 120 }}>
                        {key}:
                      </Text>
                      <Text size="xs">
                        {value === null || value === undefined
                          ? "—"
                          : typeof value === "object"
                            ? JSON.stringify(value)
                            : String(value)}
                      </Text>
                    </Group>
                  ))}
                </Stack>
                {submissionDetail.signature && (
                  <Stack gap="xs">
                    <Text size="sm" fw={500}>
                      Подпись
                    </Text>
                    {submissionDetail.signature.signer_name && (
                      <Text size="xs" c="dimmed">
                        Подписант: {submissionDetail.signature.signer_name} ·{" "}
                        {submissionDetail.signature.signer_role}
                      </Text>
                    )}
                    {(submissionDetail.signature.signature_payload as { image?: string })?.image && (
                      <Box
                        component="img"
                        src={(submissionDetail.signature.signature_payload as { image: string }).image}
                        alt="Подпись"
                        style={{
                          maxWidth: "100%",
                          height: "auto",
                          border: "1px solid var(--mantine-color-default-border)",
                          borderRadius: "var(--radius-xs)",
                        }}
                      />
                    )}
                  </Stack>
                )}
              </>
            )}
          </Stack>
        )}
      </AdminDrawer>

      <AdminDrawer
        opened={editorOpen}
        onClose={() => setEditorOpen(false)}
        position="right"
        size="lg"
        title={editingTemplate ? "Редактирование шаблона" : "Новый шаблон формы"}
      >
        <Stack gap="sm">
          <TextInput
            label="Код шаблона"
            placeholder="например, health_questionnaire"
            value={code}
            onChange={(e) => setCode(e.currentTarget.value)}
            disabled={!!editingTemplate}
          />
          <TextInput
            label="Название"
            placeholder="Анкета здоровья"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
          />
          <Group grow>
            <Switch
              label="Требуется подпись"
              checked={requiresSignature}
              onChange={(e) => setRequiresSignature(e.currentTarget.checked)}
            />
            <Switch
              label="Обязательна для завершения визита"
              checked={requiredForVisit}
              onChange={(e) => setRequiredForVisit(e.currentTarget.checked)}
            />
          </Group>
          <Switch
            label="Активен"
            checked={active}
            onChange={(e) => setActive(e.currentTarget.checked)}
          />
          <JsonInput
            label="Схема формы (JSON)"
            description="Список полей с id, label, type, required, options, sensitive"
            value={schemaJson}
            onChange={setSchemaJson}
            autosize
            minRows={12}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setEditorOpen(false)}>
              Отмена
            </Button>
            <Button onClick={handleSave} loading={upsertTemplate.isPending}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>
    </Stack>
  );
}

