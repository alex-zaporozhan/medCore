import { useCreatePatient, usePatients, useUpdatePatient } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Button, Loader, Modal, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { usePatientAiInsight, type PatientAiInsightWithStatus } from "@/hooks/useChatAi";

export default function AdminPatientsPage() {
  const { currentClinicId } = useAdminClinic();
  const [phone, setPhone] = useState("");
  const [fullName, setFullName] = useState("");
  const { data: patients, isLoading, isError, error } = usePatients({
    clinic_id: currentClinicId ?? undefined,
    phone: phone || undefined,
    full_name: fullName || undefined,
  });
  const createMutation = useCreatePatient();
  const updateMutation = useUpdatePatient();
  const [opened, { open, close }] = useDisclosure(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formPhone, setFormPhone] = useState("");
  const [formFullName, setFormFullName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [insightPatientId, setInsightPatientId] = useState<string | null>(null);
  const [insightText, setInsightText] = useState<string | null>(null);
  const [insightStatus, setInsightStatus] = useState<string | null>(null);
  const [insightError, setInsightError] = useState<string | null>(null);
  const aiInsightMutation = usePatientAiInsight(insightPatientId);

  const resetForm = () => {
    setEditingId(null);
    setFormPhone("");
    setFormFullName("");
    setFormEmail("");
  };

  const handleSave = () => {
    if (editingId) {
      updateMutation.mutate(
        { id: editingId, body: { full_name: formFullName || null, email: formEmail || null } },
        { onSuccess: () => { close(); resetForm(); } }
      );
    } else {
      createMutation.mutate(
        { phone: formPhone, full_name: formFullName || null, email: formEmail || null },
        { onSuccess: () => { close(); resetForm(); } }
      );
    }
  };

  const openCreate = () => {
    resetForm();
    open();
  };

  const openEdit = (id: string, p: { phone: string; full_name: string | null; email: string | null }) => {
    setEditingId(id);
    setFormPhone(p.phone);
    setFormFullName(p.full_name ?? "");
    setFormEmail(p.email ?? "");
    open();
  };

  if (isLoading) return <Loader />;
  if (isError) return (
    <Stack>
      <Title order={3}>Пациенты</Title>
      <span style={{ color: "red" }}>{error instanceof Error ? error.message : "Ошибка"}</span>
    </Stack>
  );

  return (
    <Stack>
      <Title order={3}>Пациенты</Title>
      <TextInput label="Телефон" placeholder="+7..." value={phone} onChange={(e) => setPhone(e.target.value)} />
      <TextInput label="ФИО" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      <Button onClick={openCreate}>Добавить пациента</Button>

      {patients?.length === 0 && (
        <EmptyStateHint title="Нет пациентов" subtitle="Добавьте пациента или измените фильтры." />
      )}

      {patients && patients.length > 0 && (
        <Table striped>
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
                <Table.Td>{p.full_name ?? "—"}</Table.Td>
                <Table.Td>{p.email ?? "—"}</Table.Td>
                <Table.Td>
                  <Stack gap={4}>
                    <Button size="xs" variant="light" onClick={() => openEdit(p.id, p)}>
                      Изменить
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={async () => {
                        setInsightPatientId(p.id);
                        setInsightText(null);
                        setInsightStatus(null);
                        setInsightError(null);
                        try {
                          const res: PatientAiInsightWithStatus = await aiInsightMutation.mutateAsync();
                          setInsightText(
                            [res.summary, res.next_best_action].filter(Boolean).join("\n\n") || res.summary
                          );
                          setInsightStatus(res.aiStatus);
                        } catch (e) {
                          setInsightError("AI‑обзор временно недоступен. Основные данные по пациенту — ниже.");
                        }
                      }}
                      loading={aiInsightMutation.isPending && insightPatientId === p.id}
                    >
                      AI‑обзор
                    </Button>
                  </Stack>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={() => { close(); resetForm(); }} title={editingId ? "Редактировать пациента" : "Новый пациент"}>
        <Stack>
          <TextInput label="Телефон" value={formPhone} onChange={(e) => setFormPhone(e.target.value)} required disabled={!!editingId} />
          <TextInput label="ФИО" value={formFullName} onChange={(e) => setFormFullName(e.target.value)} />
          <TextInput label="Email" type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} />
          <Button onClick={handleSave} loading={createMutation.isPending || updateMutation.isPending}>
            Сохранить
          </Button>
          {(createMutation.isError || updateMutation.isError) && (
            <span style={{ color: "red" }}>
              {createMutation.error instanceof Error ? createMutation.error.message : updateMutation.error instanceof Error ? updateMutation.error.message : "Ошибка"}
            </span>
          )}
          {insightError && (
            <span style={{ color: "red" }}>{insightError}</span>
          )}
          {insightText && (
            <Stack gap={4}>
              <Text size="sm" c="dimmed">
                AI‑обзор: {insightText}
              </Text>
              {insightStatus && (
                <Text size="xs" c="dimmed">
                  {insightStatus === "external_active"
                    ? "AI‑обзор (модель)."
                    : insightStatus === "fallback_local"
                      ? "AI‑обзор (локальный расчёт)."
                      : "AI‑обзор временно недоступен, основные данные по пациенту — ниже."}
                </Text>
              )}
            </Stack>
          )}
        </Stack>
      </Modal>
    </Stack>
  );
}
