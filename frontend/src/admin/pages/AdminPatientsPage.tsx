import { usePatients, useAdminFormTemplates, useSendFormLink, useDeletePatient, useAdminSession } from "@/hooks";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { ActionIcon, Alert, Button, Group, HoverCard, Menu, Modal, Select, Stack, Table, Text, TextInput } from "@mantine/core";
import { AdminDrawer } from "@/shared/ui";
import { IconDotsVertical, IconEdit, IconSend, IconTrash, IconUserPlus } from "@tabler/icons-react";
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { PatientEntityDrawer } from "@/admin/components/entity/PatientEntityDrawer";
import type { Patient } from "@/api/types";
import { ADMIN_PERM_PATIENTS_PII_READ } from "@/shared/adminPermissions";

export default function AdminPatientsPage() {
  const { data: adminSession, isLoading: sessionLoading } = useAdminSession();
  const { currentClinicId } = useAdminClinic();
  const [searchParams, setSearchParams] = useSearchParams();
  const [phone, setPhone] = useState("");
  const [fullName, setFullName] = useState("");
  const [visitFrom, setVisitFrom] = useState("");
  const [visitTo, setVisitTo] = useState("");
  const { data: patients, isLoading, isError, error } = usePatients({
    clinic_id: currentClinicId ?? undefined,
    phone: phone || undefined,
    full_name: fullName || undefined,
    visited_from: visitFrom || undefined,
    visited_to: visitTo || undefined,
  });
  const [patientDrawer, setPatientDrawer] = useState<{
    mode: "create" | "edit" | "view";
    patient: Patient | null;
    initialForm?: { phone: string; full_name: string; email: string };
  } | null>(null);
  const [sendFormPatientId, setSendFormPatientId] = useState<string | null>(null);
  const [formTemplateId, setFormTemplateId] = useState<string | null>(null);
  const [formSendVia, setFormSendVia] = useState<"whatsapp" | "sms" | "copy_only">("copy_only");
  const { data: formTemplates } = useAdminFormTemplates();
  const sendFormLink = useSendFormLink();
  const deletePatient = useDeletePatient();
  const [patientToDelete, setPatientToDelete] = useState<Patient | null>(null);
  const queryClient = useQueryClient();

  const patientIdFocus = searchParams.get("patient_id");

  useEffect(() => {
    if (!patientIdFocus || !patients?.length) return;
    const p = patients.find((x) => x.id === patientIdFocus);
    if (p) setPatientDrawer({ mode: "view", patient: p });
  }, [patientIdFocus, patients]);

  const openCreate = () => {
    setPatientDrawer({ mode: "create", patient: null, initialForm: { phone: "", full_name: "", email: "" } });
  };

  const openEdit = (p: Patient) => {
    setPatientDrawer({ mode: "edit", patient: p });
  };

  const openView = (p: Patient) => {
    setPatientDrawer({ mode: "view", patient: p });
  };

  if (sessionLoading) return <PageSkeleton variant="table" rows={8} />;
  if (adminSession && !adminSession.permissions?.includes(ADMIN_PERM_PATIENTS_PII_READ)) {
    return (
      <Stack>
        <ContextBar title="Пациенты" />
        <Alert color="yellow" title="Нет доступа">
          Раздел с персональными данными пациентов доступен только администраторам и ролям с соответствующим правом
          (не врачам и линейному персоналу без явного разрешения).
        </Alert>
      </Stack>
    );
  }

  if (isLoading) return <PageSkeleton variant="table" rows={8} />;
  if (isError) {
    return (
      <Stack>
        <ContextBar title="Пациенты" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Пациенты" actions={<Button onClick={openCreate}>Добавить пациента</Button>} />
      <TextInput label="Телефон" placeholder="+7..." value={phone} onChange={(e) => setPhone(e.target.value)} />
      <TextInput label="ФИО" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      <Group grow align="flex-end">
        <TextInput
          label="Визит с (дата)"
          type="date"
          value={visitFrom}
          onChange={(e) => setVisitFrom(e.currentTarget.value)}
        />
        <TextInput
          label="Визит по (дата)"
          type="date"
          value={visitTo}
          onChange={(e) => setVisitTo(e.currentTarget.value)}
        />
      </Group>
      {(visitFrom || visitTo) && !currentClinicId ? (
        <Text size="sm" c="orange">
          Для фильтра по датам визита выберите клинику в шапке.
        </Text>
      ) : null}
      {patientIdFocus &&
      patients &&
      !patients.some((x) => x.id === patientIdFocus) ? (
        <Alert color="yellow" title="Пациент не в текущем списке">
          В адресе указан ID пациента, но при активных фильтрах его нет в таблице. Сбросьте фильтры или откройте карточку из
          расписания.
        </Alert>
      ) : null}

      {patients?.length === 0 && (
        <EmptyState
          title="Нет пациентов"
          description="Добавьте первого пациента или измените фильтры."
          icon={<IconUserPlus size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
          action={{ label: "Добавить пациента", onClick: openCreate }}
        />
      )}

      {patients && patients.length > 0 && (
        <Table striped verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Телефон</Table.Th>
              <Table.Th>ФИО</Table.Th>
              <Table.Th>Email</Table.Th>
              <Table.Th>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {patients.map((p) => (
              <Table.Tr key={p.id}>
                <Table.Td>{p.phone}</Table.Td>
                <Table.Td>
                  <HoverCard openDelay={300} width={240} shadow="md">
                    <HoverCard.Target>
                      <Text
                        span
                        style={{ cursor: "pointer" }}
                        onClick={() => openView(p)}
                      >
                        {p.full_name ?? "—"}
                      </Text>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                      <Stack gap={4}>
                        <Text size="sm" fw={500}>{p.full_name ?? p.phone}</Text>
                        <Text size="xs" c="dimmed">Телефон: {p.phone}</Text>
                        {p.email && <Text size="xs" c="dimmed">Email: {p.email}</Text>}
                        <Text size="xs" c="dimmed">Клик — открыть карточку</Text>
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </Table.Td>
                <Table.Td>{p.email ?? "—"}</Table.Td>
                <Table.Td onClick={(e) => e.stopPropagation()}>
                  <Menu position="bottom-end" shadow="sm">
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => openEdit(p)}>
                        Редактировать
                      </Menu.Item>
                      <Menu.Item leftSection={<IconUserPlus size={14} />} onClick={() => openView(p)}>
                        Открыть карточку
                      </Menu.Item>
                      <Menu.Item
                        leftSection={<IconSend size={14} />}
                        onClick={() => {
                          setSendFormPatientId(p.id);
                          setFormTemplateId(null);
                          setFormSendVia("copy_only");
                        }}
                      >
                        Отправить форму
                      </Menu.Item>
                      <Menu.Item
                        leftSection={<IconTrash size={14} />}
                        color="red"
                        onClick={() => setPatientToDelete(p)}
                      >
                        Удалить
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <PatientEntityDrawer
        opened={patientDrawer !== null}
        onClose={() => {
          setPatientDrawer(null);
          if (searchParams.get("patient_id")) {
            const next = new URLSearchParams(searchParams);
            next.delete("patient_id");
            setSearchParams(next);
          }
        }}
        patient={patientDrawer?.patient ?? null}
        mode={patientDrawer?.mode ?? "view"}
        initialForm={patientDrawer?.initialForm}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ["patients"] })}
      />

      <AdminDrawer
        opened={sendFormPatientId !== null}
        onClose={() => { setSendFormPatientId(null); setFormTemplateId(null); }}
        position="right"
        size="sm"
        title="Отправить форму"
      >
        {sendFormPatientId && (
          <Stack gap="md">
            <Select
              label="Шаблон формы"
              placeholder="Выберите шаблон"
              data={(formTemplates ?? []).map((t) => ({ value: t.id, label: t.name }))}
              value={formTemplateId}
              onChange={(v) => setFormTemplateId(v)}
              searchable
            />
            <Select
              label="Куда отправить"
              data={[
                { value: "copy_only", label: "Скопировать ссылку" },
                { value: "whatsapp", label: "WhatsApp" },
                { value: "sms", label: "SMS" },
              ]}
              value={formSendVia}
              onChange={(v) => setFormSendVia((v as "whatsapp" | "sms" | "copy_only") || "copy_only")}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSendFormPatientId(null)}>
                Отмена
              </Button>
              <Button
                onClick={() => {
                  sendFormLink.mutate(
                    { patient_id: sendFormPatientId, template_id: formTemplateId!, send_via: formSendVia },
                    {
                      onSuccess: (res) => {
                        if (res.sent) setSendFormPatientId(null);
                        if (res.sent && formSendVia === "copy_only" && res.url) {
                          try { navigator.clipboard.writeText(res.url); } catch { /* ignore */ }
                        }
                      },
                    }
                  );
                }}
                loading={sendFormLink.isPending}
                disabled={!formTemplateId}
              >
                Отправить ссылку
              </Button>
            </Group>
          </Stack>
        )}
      </AdminDrawer>

      <Modal
        opened={patientToDelete !== null}
        onClose={() => setPatientToDelete(null)}
        title="Удалить пациента?"
      >
        <Stack gap="md">
          <Text size="sm">
            {patientToDelete
              ? `Вы уверены, что хотите удалить пациента ${patientToDelete.full_name ?? patientToDelete.phone}? Это действие нельзя отменить.`
              : ""}
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPatientToDelete(null)}>
              Отмена
            </Button>
            <Button
              color="red"
              loading={deletePatient.isPending}
              onClick={() => {
                if (!patientToDelete) return;
                deletePatient.mutate(patientToDelete.id, {
                  onSuccess: () => {
                    setPatientToDelete(null);
                    queryClient.invalidateQueries({ queryKey: ["patients"] });
                    queryClient.invalidateQueries({ queryKey: ["admin-bookings"] });
                  },
                });
              }}
            >
              Удалить
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
