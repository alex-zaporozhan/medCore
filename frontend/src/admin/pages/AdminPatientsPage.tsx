import { usePatients, useAdminFormTemplates, useSendFormLink, useDeletePatient, useAdminSession } from "@/hooks";
import { ContextBar } from "@/shared/ui/ContextBar";
import {
  EmptyState,
  PageSkeleton,
  QueryErrorAlert,
  AdminDataTableToolbar,
  AdminDataTableSurface,
  ADMIN_TABLE_PROPS,
} from "@/shared/ui";
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
import { useTranslation } from "react-i18next";

export default function AdminPatientsPage() {
  const { t } = useTranslation("directory");
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
        <ContextBar title={t("patients.title")} />
        <Alert color="yellow" title={t("patients.noAccessTitle")}>
          {t("patients.noAccessBody")}
        </Alert>
      </Stack>
    );
  }

  if (isLoading) return <PageSkeleton variant="table" rows={8} />;
  if (isError) {
    return (
      <Stack>
        <ContextBar title={t("patients.title")} />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title={t("patients.title")} actions={<Button onClick={openCreate}>{t("patients.add")}</Button>} />
      <AdminDataTableToolbar>
        <Stack gap="sm">
          <TextInput label={t("phone")} placeholder="+7..." value={phone} onChange={(e) => setPhone(e.target.value)} />
          <TextInput label={t("fullName")} value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <Group grow align="flex-end">
            <TextInput
              label={t("patients.visitFrom")}
              type="date"
              value={visitFrom}
              onChange={(e) => setVisitFrom(e.currentTarget.value)}
            />
            <TextInput
              label={t("patients.visitTo")}
              type="date"
              value={visitTo}
              onChange={(e) => setVisitTo(e.currentTarget.value)}
            />
          </Group>
        </Stack>
      </AdminDataTableToolbar>
      {(visitFrom || visitTo) && !currentClinicId ? (
        <Text size="sm" c="orange">
          {t("patients.pickClinicForVisitFilter")}
        </Text>
      ) : null}
      {patientIdFocus &&
      patients &&
      !patients.some((x) => x.id === patientIdFocus) ? (
        <Alert color="yellow" title={t("patients.notInListTitle")}>
          {t("patients.notInListBody")}
        </Alert>
      ) : null}

      {patients?.length === 0 && (
        <EmptyState
          title={t("patients.emptyTitle")}
          description={t("patients.emptyHint")}
          icon={<IconUserPlus size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
          action={{ label: t("patients.add"), onClick: openCreate }}
        />
      )}

      {patients && patients.length > 0 && (
        <AdminDataTableSurface>
          <Table {...ADMIN_TABLE_PROPS}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("phone")}</Table.Th>
                <Table.Th>{t("fullName")}</Table.Th>
                <Table.Th>{t("email")}</Table.Th>
                <Table.Th>{t("actions")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {patients.map((p) => (
              <Table.Tr key={p.id} className="data-table-clickable-row">
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
                        <Text size="xs" c="dimmed">{t("patients.hoverPhone", { phone: p.phone })}</Text>
                        {p.email && <Text size="xs" c="dimmed">Email: {p.email}</Text>}
                        <Text size="xs" c="dimmed">{t("patients.hoverOpen")}</Text>
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </Table.Td>
                <Table.Td>{p.email ?? "—"}</Table.Td>
                <Table.Td onClick={(e) => e.stopPropagation()}>
                  <Menu position="bottom-end" shadow="sm">
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label={t("actions")}>
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => openEdit(p)}>
                        {t("edit")}
                      </Menu.Item>
                      <Menu.Item leftSection={<IconUserPlus size={14} />} onClick={() => openView(p)}>
                        {t("openCard")}
                      </Menu.Item>
                      <Menu.Item
                        leftSection={<IconSend size={14} />}
                        onClick={() => {
                          setSendFormPatientId(p.id);
                          setFormTemplateId(null);
                          setFormSendVia("copy_only");
                        }}
                      >
                        {t("patients.sendForm")}
                      </Menu.Item>
                      <Menu.Item
                        leftSection={<IconTrash size={14} />}
                        color="red"
                        onClick={() => setPatientToDelete(p)}
                      >
                        {t("delete")}
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Table.Td>
              </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </AdminDataTableSurface>
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
        title={t("patients.sendFormTitle")}
      >
        {sendFormPatientId && (
          <Stack gap="md">
            <Select
              label={t("patients.formTemplate")}
              placeholder={t("patients.formTemplatePlaceholder")}
              data={(formTemplates ?? []).map((tpl) => ({ value: tpl.id, label: tpl.name }))}
              value={formTemplateId}
              onChange={(v) => setFormTemplateId(v)}
              searchable
            />
            <Select
              label={t("patients.sendVia")}
              data={[
                { value: "copy_only", label: t("patients.copyLink") },
                { value: "whatsapp", label: "WhatsApp" },
                { value: "sms", label: "SMS" },
              ]}
              value={formSendVia}
              onChange={(v) => setFormSendVia((v as "whatsapp" | "sms" | "copy_only") || "copy_only")}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSendFormPatientId(null)}>
                {t("cancel")}
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
                {t("patients.sendLink")}
              </Button>
            </Group>
          </Stack>
        )}
      </AdminDrawer>

      <Modal
        opened={patientToDelete !== null}
        onClose={() => setPatientToDelete(null)}
        title={t("patients.deleteTitle")}
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            {patientToDelete
              ? t("patients.deleteConfirm", { name: patientToDelete.full_name ?? patientToDelete.phone })
              : ""}
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPatientToDelete(null)}>
              {t("cancel")}
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
              {t("delete")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
