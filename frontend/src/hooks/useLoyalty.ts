import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { api, authApi } from "@/api/client";
import type {
  SubscriptionPackage,
  CustomerSubscription,
  Wallet,
  WalletTransaction,
  PatientLoyaltyMeResponse,
  PatientLoyaltyHistoryResponse,
  AdminLoyaltySummaryByContactResponse,
  LoyaltyCampaignSettings,
  LoyaltyCampaignRunResult,
} from "@/api/types";

export function useLoyaltyPackages() {
  return useQuery({
    queryKey: ["admin", "loyalty", "packages"],
    queryFn: () => api.get<SubscriptionPackage[]>("/v1/admin/loyalty/packages"),
  });
}

export function useCustomerSubscriptions(patientId: string | null, onlyActive: boolean = false) {
  return useQuery({
    queryKey: ["admin", "loyalty", "customer-subscriptions", patientId, onlyActive],
    queryFn: () =>
      api.get<CustomerSubscription[]>(
        `/v1/admin/loyalty/customer-subscriptions?patient_id=${patientId}${
          onlyActive ? "&only_active=true" : ""
        }`,
      ),
    enabled: !!patientId,
  });
}

export function useWallets(patientId: string | null) {
  return useQuery({
    queryKey: ["admin", "loyalty", "wallets", patientId],
    queryFn: () =>
      api.get<Wallet[]>(`/v1/admin/loyalty/wallets?patient_id=${patientId}`),
    enabled: !!patientId,
  });
}

export function useWalletTransactions(walletId: string | null) {
  return useQuery({
    queryKey: ["admin", "loyalty", "wallet-transactions", walletId],
    queryFn: () =>
      api.get<WalletTransaction[]>(
        `/v1/admin/loyalty/wallets/${walletId}/transactions`,
      ),
    enabled: !!walletId,
  });
}

export function usePatientLoyaltyMe(accessToken: string | null) {
  return useQuery({
    queryKey: ["patient", "loyalty", "me"],
    queryFn: () =>
      authApi(accessToken).get<PatientLoyaltyMeResponse>("/v1/patient/loyalty/me"),
    enabled: !!accessToken,
  });
}

export function usePatientLoyaltyHistory(accessToken: string | null) {
  return useQuery({
    queryKey: ["patient", "loyalty", "history"],
    queryFn: () =>
      authApi(accessToken).get<PatientLoyaltyHistoryResponse>(
        "/v1/patient/loyalty/history",
      ),
    enabled: !!accessToken,
  });
}

export function useAdminLoyaltySummaryByContact(contactId: string | null) {
  return useQuery({
    queryKey: ["admin", "loyalty", "summary-by-contact", contactId],
    queryFn: () =>
      api.get<AdminLoyaltySummaryByContactResponse>(
        `/v1/admin/loyalty/summary-by-contact?contact_id=${contactId}`,
      ),
    enabled: !!contactId,
  });
}

/** B6.1 Family Sharing: add a family member to a customer subscription. */
export function useLoyaltyCampaignSettings(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "loyalty", "campaign-settings"],
    queryFn: () =>
      api.get<LoyaltyCampaignSettings>("/v1/admin/loyalty/campaign-settings"),
    enabled: !!clinicId,
  });
}

export function useUpdateLoyaltyCampaignSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<LoyaltyCampaignSettings>) =>
      api.patch<LoyaltyCampaignSettings>(
        "/v1/admin/loyalty/campaign-settings",
        body,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "loyalty", "campaign-settings"],
      });
    },
  });
}

export function useRunLoyaltyCampaigns() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<LoyaltyCampaignRunResult>(
        "/v1/admin/loyalty/campaigns/run",
        {},
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tasks"] });
      queryClient.invalidateQueries({
        queryKey: ["admin", "loyalty", "campaign-settings"],
      });
    },
  });
}

export function useAddFamilyMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      subscriptionId,
      patientId,
    }: {
      subscriptionId: string;
      patientId: string;
    }) =>
      api.post<unknown>(
        `/v1/admin/loyalty/customer-subscriptions/${subscriptionId}/family-members`,
        { patient_id: patientId },
      ),
    onSuccess: (_data, _variables) => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "loyalty", "summary-by-contact"],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin", "loyalty", "customer-subscriptions"],
      });
    },
  });
}