import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { api } from "@/api/client";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { Paper, Stack, Switch, Text } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";

interface PolicyRead {
  allow_patient_disable_discount_notifications: boolean;
  allow_patient_disable_reminders: boolean;
  allow_patient_disable_all_notifications: boolean;
}

export default function AdminNotificationPolicyPage() {
  const { currentClinicId } = useAdminClinic();
  const queryClient = useQueryClient();
  const { data: policy, isLoading, isError, error } = useQuery({
    queryKey: ["admin-notification-policy", currentClinicId],
    queryFn: () =>
      api.get<PolicyRead>(
        `/v1/admin/clinics/${currentClinicId}/notification-policy`
      ),
    enabled: !!currentClinicId,
  });

  const updatePolicy = useMutation({
    mutationFn: (body: Partial<PolicyRead>) =>
      api.put<PolicyRead>(
        `/v1/admin/clinics/${currentClinicId}/notification-policy`,
        body
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-notification-policy", currentClinicId],
      });
    },
  });

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
        <Text c="red">{error instanceof Error ? error.message : "Ошибка загрузки"}</Text>
      </Stack>
    );
  }

  const p = policy!;

  const handleChange = (key: keyof PolicyRead, value: boolean) => {
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
