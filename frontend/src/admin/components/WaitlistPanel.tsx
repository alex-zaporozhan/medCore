import type { WaitlistEntry } from "@/hooks/useAdminWaitlist";
import { useCancelWaitlistEntry } from "@/hooks/useAdminWaitlist";
import { Box, Button, Card, Stack, Text, Title } from "@mantine/core";

/** patient_id -> display name (ФИО или телефон) */
interface WaitlistPanelProps {
  clinicId: string | null;
  doctorId: string | null;
  date: string;
  entries: WaitlistEntry[] | undefined;
  patientNameMap?: Record<string, string>;
}

export function WaitlistPanel({
  clinicId,
  doctorId,
  date: _date,
  entries,
  patientNameMap,
}: WaitlistPanelProps) {
  const cancelMutation = useCancelWaitlistEntry(clinicId);

  if (!doctorId) {
    return null;
  }

  const prefs = (e: WaitlistEntry) => e.time_preferences_json as { from?: string; to?: string } | null;

  return (
    <Box>
      <Title order={4} mb="sm">
        Очередь ожидания
      </Title>
      {entries && entries.length === 0 && (
        <Text size="sm" c="dimmed">
          На выбранную дату очередь пуста.
        </Text>
      )}
      <Stack gap="sm">
        {entries?.map((entry) => (
          <Card
            key={entry.id}
            withBorder
            padding="sm"
            radius="md"
            style={{ background: "var(--bg-card)" }}
          >
            <Stack gap={4}>
              <Text size="sm" fw={500}>
                Пациент: {patientNameMap?.[entry.patient_id] ?? entry.patient_id}
              </Text>
              <Text size="xs" c="dimmed">
                Предпочитаемое время:{" "}
                {(() => {
                  const p = prefs(entry);
                  return p?.from && p?.to
                    ? `${String(p.from).slice(0, 5)}–${String(p.to).slice(0, 5)}`
                    : "не указано";
                })()}
              </Text>
              <Text size="xs" c="dimmed">
                Статус: {entry.status}
              </Text>
              <Box style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <Button
                  size="xs"
                  variant="subtle"
                  color="red"
                  onClick={() => cancelMutation.mutate(entry.id)}
                  loading={cancelMutation.isPending}
                >
                  Отменить ожидание
                </Button>
              </Box>
            </Stack>
          </Card>
        ))}
      </Stack>
    </Box>
  );
}

