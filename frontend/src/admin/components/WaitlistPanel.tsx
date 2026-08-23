import { useCancelWaitlistEntry, type WaitlistEntry } from "@/hooks";
import { Box, Button, Card, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { displayPersonName } from "@/shared/ui/personNameFallback";

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
  const { t } = useTranslation("schedule");
  const cancelMutation = useCancelWaitlistEntry(clinicId);

  if (!doctorId) {
    return null;
  }

  const prefs = (e: WaitlistEntry) => e.time_preferences_json as { from?: string; to?: string } | null;

  return (
    <Box>
      <Title order={4} mb="sm">
        {t("waitlistPanel.title")}
      </Title>
      {entries && entries.length === 0 && (
        <Text size="sm" c="dimmed">
          {t("waitlistPanel.empty")}
        </Text>
      )}
      <Stack gap="sm">
        {entries?.map((entry) => {
          const p = prefs(entry);
          const preferred =
            p?.from && p?.to
              ? `${String(p.from).slice(0, 5)}–${String(p.to).slice(0, 5)}`
              : t("waitlistPanel.unspecified");
          return (
            <Card
              key={entry.id}
              withBorder
              padding="sm"
              radius="md"
              style={{ background: "var(--bg-card)" }}
            >
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  {t("waitlistPanel.patientLine", {
                    name: displayPersonName(patientNameMap?.[entry.patient_id], entry.patient_id),
                  })}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("waitlistPanel.preferredTime", { value: preferred })}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("waitlistPanel.statusLine", { status: entry.status })}
                </Text>
                <Box style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <Button
                    size="xs"
                    variant="subtle"
                    color="red"
                    onClick={() => cancelMutation.mutate(entry.id)}
                    loading={cancelMutation.isPending}
                  >
                    {t("waitlistPanel.cancelWait")}
                  </Button>
                </Box>
              </Stack>
            </Card>
          );
        })}
      </Stack>
    </Box>
  );
}
