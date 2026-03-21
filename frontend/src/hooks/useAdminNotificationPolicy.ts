import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface NotificationPolicyRead {
  allow_patient_disable_discount_notifications: boolean;
  allow_patient_disable_reminders: boolean;
  allow_patient_disable_all_notifications: boolean;
}

export function useAdminNotificationPolicy(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.adminNotificationPolicy(clinicId),
    queryFn: () =>
      api.get<NotificationPolicyRead>(
        `/v1/admin/clinics/${clinicId}/notification-policy`
      ),
    enabled: !!clinicId,
  });
}

export function useUpdateAdminNotificationPolicyMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<NotificationPolicyRead>) =>
      api.put<NotificationPolicyRead>(
        `/v1/admin/clinics/${clinicId}/notification-policy`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminNotificationPolicy(clinicId) });
    },
  });
}
