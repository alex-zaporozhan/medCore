import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAdminNotificationPolicy,
  useUpdateAdminNotificationPolicyMutation,
} from "@/hooks/useAdminNotificationPolicy";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { QueryErrorAlert } from "@/shared/ui";
import { Paper, Stack, Switch, Text } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";

export default function AdminNotificationPolicyPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: policy, isLoading, isError, error } = useAdminNotificationPolicy(
    currentClinicId ?? null
  );
  const updatePolicy = useUpdateAdminNotificationPolicyMutation(currentClinicId ?? null);

  if (!currentClinicId) {
    return (
      <Stack>
        <ContextBar title="Политика уведомлений" />
        <Text c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }
  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Политика уведомлений" />
        <DataSkeleton lines={4} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <ContextBar title="Политика уведомлений" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  const p = policy!;

  const handleChange = (
    key:
      | "allow_patient_disable_discount_notifications"
      | "allow_patient_disable_reminders"
      | "allow_patient_disable_all_notifications",
    value: boolean
  ) => {
    updatePolicy.mutate({ [key]: value });
  };

  return (
    <Stack gap="md">
      <ContextBar title="Политика уведомлений" />
      <Text size="sm" c="dimmed">
        Если переключатель выключен, пациент не сможет отключить этот тип уведомлений в приложении; изменение возможно только через обращение в клинику.
      </Text>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="md">
          <Switch
            label="Клиент может сам отключить оповещения о скидках и акциях"
            checked={p.allow_patient_disable_discount_notifications}
            onChange={(e) =>
              handleChange("allow_patient_disable_discount_notifications", e.currentTarget.checked)
            }
            disabled={updatePolicy.isPending}
          />
          <Switch
            label="Клиент может сам отключить напоминания о приёме"
            checked={p.allow_patient_disable_reminders}
            onChange={(e) =>
              handleChange("allow_patient_disable_reminders", e.currentTarget.checked)
            }
            disabled={updatePolicy.isPending}
          />
          <Switch
            label="Клиент может сам отключить все уведомления"
            checked={p.allow_patient_disable_all_notifications}
            onChange={(e) =>
              handleChange("allow_patient_disable_all_notifications", e.currentTarget.checked)
            }
            disabled={updatePolicy.isPending}
          />
        </Stack>
      </Paper>
    </Stack>
  );
}
