/**
 * Баррель доменного слоя данных (техпаспорт §4.1). Новый `hooks/use*.ts` — добавить `from "./use…"` сюда;
 * регресс ловит `hooks/__tests__/hooksBarrelParity.test.ts`.
 */
export { useDoctors, useDoctor } from "./useDoctors";
export { useDoctorSchedule, useDoctorScheduleAdmin, useAdminSchedule } from "./useDoctorSchedule";
export {
  useWorkingHours,
  useCreateOrUpdateWorkingHours,
  useUpdateWorkingHours,
  useDeleteWorkingHours,
  useAbsence,
  useCreateAbsence,
  useDeleteAbsence,
} from "./useDoctorScheduleConfig";
export { useServices, useService } from "./useServices";
export { usePatients, usePatient } from "./usePatients";
export {
  useCheckoutInfo,
  useAdminBookings,
  useRescheduleBookingAdmin,
  useCreateAdminBooking,
  usePatchBookingAdmin,
  useCancelBookingAdmin,
  useCompleteBookingAdmin,
} from "./useAdminBookings";
export {
  usePatientBookings,
  useCreatePatientBooking,
  useCancelPatientBooking,
} from "./usePatientBookings";
export {
  useReportsDashboard,
  useReportsNoShow,
  useReportsRevenue,
} from "./useReports";
export { useAgreement, useSendCode, useVerifyCode } from "./useAuth";
export { useCreatePayment } from "./usePayments";
export {
  useCreateDoctor,
  useUpdateDoctor,
  useDeleteDoctor,
} from "./useDoctorsMutations";
export { useCreatePatient, useUpdatePatient, useDeletePatient } from "./usePatientsMutations";
export {
  useCreateService,
  useUpdateService,
  useDeleteService,
} from "./useServicesMutations";
export {
  useAdminClinicServices,
  useCreateAdminClinicService,
  useUpdateAdminClinicService,
  useDeleteAdminClinicService,
} from "./useAdminClinicServices";
export { usePublicClinicServices } from "./usePublicClinicServices";
export {
  useClinics,
  useUpdateClinicMutation,
  useCreateClinicMutation,
} from "./useClinics";
export {
  useAdminAdmins,
  useCreateAdminMutation,
  usePatchAdminEmploymentMutation,
} from "./useAdminAdmins";
export type { AdminUserRow } from "./useAdminAdmins";
export { useAdminSession } from "./useAdminSession";
export type { AdminSessionPayload } from "./useAdminSession";
export {
  useAdminTasksList,
  useAdminTasksMyFocus,
  useAdminTasksAi,
  useAdminTasksOpen,
  useCreateAdminTaskMutation,
  useClaimAdminTaskMutation,
  useUpdateAdminTaskStatusMutation,
  useUpdateAdminTaskMetaMutation,
  useReorderAdminTasksMutation,
  useBulkUpdateAdminTaskStatusMutation,
  useTaskTransitions,
  useTaskWipPolicies,
  useTaskCalendarContext,
  useInviteTaskCalendarParticipants,
  useTaskComments,
  usePostTaskComment,
} from "./useAdminTasks";
export type {
  AdminTaskRow,
  AdminTaskOpenRow,
  TaskCommentRow,
  TaskTransitionRow,
  TaskCalendarEventContextRow,
  TaskCalendarParticipantAckRow,
} from "./useAdminTasks";
export { useAdminTaskDetails } from "./useAdminTaskDetails";
export {
  useAdminDiscounts,
  useCreateAdminDiscountMutation,
  useUpdateAdminDiscountMutation,
  useDeleteAdminDiscountMutation,
} from "./useAdminDiscounts";
export type { DiscountRead, DiscountCreate } from "./useAdminDiscounts";
export {
  useAdminClientReference,
  useUpdateAdminClientReferenceMutation,
} from "./useAdminClientReference";
export type { ClientReferenceResponse } from "./useAdminClientReference";
export {
  useAdminNotificationPolicy,
  useUpdateAdminNotificationPolicyMutation,
} from "./useAdminNotificationPolicy";
export type { NotificationPolicyRead } from "./useAdminNotificationPolicy";
export {
  useAdminAgreementSettings,
  useUpdateAdminAgreementSettingsMutation,
} from "./useAdminAgreements";
export type { AgreementSettings } from "./useAdminAgreements";
export {
  useAdminIntegrationSettings1c,
  useUpdateAdminIntegrationSettings1cMutation,
} from "./useAdminIntegrations";
export type { IntegrationSettings1c } from "./useAdminIntegrations";
export {
  useAdminRetentionSegments,
  useAdminRetentionCampaignsRoi,
} from "./useAdminRetention";
export type { RetentionSegment, RetentionCampaignRoi } from "./useAdminRetention";
export {
  OMNI_VAULT_EXPORT_PRESETS,
  useOmniVaultMediaGallery,
  useOmniVaultExportPresets,
  useRequestOmniVaultBackupMutation,
  useOmniVaultBackupStatus,
} from "./useAdminOmniVault";
export type { OmniVaultMediaResponse, OmniVaultExportPreset } from "./useAdminOmniVault";
export {
  useAdminAiConflictReport,
} from "./useAdminAiReports";
export type {
  ConflictItem,
  ConflictSummary,
  ConflictReportResponse,
} from "./useAdminAiReports";
export {
  useAdminClinicAiSettings,
  useAdminAiStatus,
  useUpdateAdminClinicAiSettingsMutation,
} from "./useAdminAiSettings";
export type {
  AdminClinicAiSettings,
  AiMode,
  AdminAiStatusResponse,
} from "./useAdminAiSettings";
export {
  usePatientConversation,
  usePatientChatMessages,
  useSendPatientMessage,
  useDeletePatientMessage,
  usePatientMarkRead,
} from "./usePatientChat";
export {
  useAdminChatConversations,
  useAdminChatMessages,
  useSendAdminMessage,
  useAdminAssignConversation,
  useAdminChatMarkRead,
  useDeleteAdminMessage,
} from "./useAdminChat";
export { useSetClinicPaymentGatewayCredentials } from "./useAdminPaymentGateway";
export {
  useCrmPipelines,
  useCrmStages,
  useCrmLeads,
  useCrmKanbanStageLeadsInfinite,
  useCrmLeadDetails,
  useUpdateLeadStage,
  useCreateLeadNote,
  usePipelineStageSemantics,
  useAiLeadSummary,
  useAiSuggestNextStage,
  useAiUpdateLeadStage,
  useAiCreateTaskForLead,
  useAiIgnoreLeadRecommendation,
} from "./useCrmLeads";
export {
  useCashboxes,
  useFinanceTransactions,
  useFinanceLiability,
  useCreateFinanceTransaction,
} from "./useErpFinance";
export { usePayrollPolicies, useSalaryTransactions } from "./useErpPayroll";
export {
  useInventoryProducts,
  useWarehouses,
  useServiceConsumables,
  useInventoryTransactions,
  useInventoryStock,
} from "./useErpInventory";
export {
  useLoyaltyPackages,
  useCustomerSubscriptions,
  useWallets,
  useWalletTransactions,
  usePatientLoyaltyMe,
  usePatientLoyaltyHistory,
  useAdminLoyaltySummaryByContact,
  useLoyaltyCampaignSettings,
  useUpdateLoyaltyCampaignSettings,
  useRunLoyaltyCampaigns,
  useAddFamilyMember,
} from "./useLoyalty";
export {
  useAdminFormTemplates,
  useAdminFormSubmissions,
  useAdminFormSubmissionDetail,
  useSendFormLink,
  useUpsertAdminFormTemplate,
  usePatientPendingForms,
  useSubmitPatientForm,
} from "./useForms";
export { useAdminSearch } from "./useAdminSearch";
export { useAiAgent } from "./useAiAgent";
export { useEffectiveAiFeatureGate } from "./useEffectiveAiFeatureGate";
export {
  useRevenueHunterSaved,
  isRevenueHunterEnabled,
} from "./useRevenueHunter";
export { useAvailableAiTools } from "./useAvailableAiTools";
export {
  useMarketingAttributionSummary,
  useMarketingCampaigns,
  useMarketingInsights,
  useMarketingAttributionDrillDown,
} from "./useMarketingAttribution";
export {
  useAdminReportsDashboard,
  useAdminReportsDashboardAggregate,
  useAdminReportsDashboardByClinics,
  useAdminReportsNoShow,
  useAdminReportsRevenue,
  useOwnerDashboard,
} from "./useAdminReports";
export {
  useAdminOmniChats,
  useAdminOmniChatDetail,
  useAdminOmniChatMessages,
  useAdminOmniChatMessagesInfinite,
  useOmniChatSse,
  useOmniQuickReplies,
  usePatchOmniChat,
  useSendAdminOmniMessage,
  useHideAdminOmniMessage,
  useUpdateOmniChatAiMode,
} from "./useAdminOmniChat";
export {
  useAdminRecallSegments,
  useCreateRecallSegment,
  useUpdateRecallSegment,
  useDeleteRecallSegment,
  useAdminRecallTemplates,
  useCreateRecallTemplate,
  useUpdateRecallTemplate,
  useDeleteRecallTemplate,
  useAdminRecallCampaigns,
  useCreateRecallCampaign,
  useUpdateRecallCampaign,
  useDeleteRecallCampaign,
  useRunRecallCampaign,
  useAdminRecallAutomations,
  useCreateRecallAutomation,
  useUpdateRecallAutomation,
  useDeleteRecallAutomation,
  useAdminRecallLogs,
} from "./useAdminRecall";
export {
  useOwnerOmniChannels,
  useCreateOwnerOmniChannel,
  useUpdateOwnerOmniChannel,
  useSetOwnerOmniChannelCredentials,
} from "./useOwnerOmniChannels";
export { useOwnerOmniAiSettings, useUpdateOwnerOmniAiSettings } from "./useOwnerOmniAiSettings";
export { useChannelConfigs, useUpsertChannelConfig } from "./useChannelConfigs";
export {
  useAdminPrepaymentPolicies,
  useCreatePrepaymentPolicy,
  useUpdatePrepaymentPolicy,
  useDeletePrepaymentPolicy,
} from "./useAdminPrepayment";
export { useStickerSets } from "./useStickers";
export {
  useAttentionFeed,
  useCloseFollowUp,
  useCreateAttentionFeedTask,
} from "./useAttentionFeed";
export {
  useConversationSummary,
  useSuggestReply,
  usePatientAiInsight,
} from "./useChatAi";
export { usePublicFeed, usePublicStories } from "./usePublicFeed";
export {
  useAdminPromoPosts,
  useCreatePromoPost,
  useUpdatePromoPost,
  useDeletePromoPost,
  useAdminStories,
  useCreateStory,
  useUpdateStory,
  useDeleteStory,
} from "./useAdminMarketing";
export {
  useAdminWaitlistEntries,
  useCreateWaitlistEntry,
  useUpdateWaitlistEntry,
  useDeleteWaitlistEntry,
  useAdminQueuePolicy,
  useUpsertQueuePolicy,
  useAdminWaitlist,
  useCancelWaitlistEntry,
} from "./useAdminWaitlist";

export * from "./useStaffCollab";

/** Публичные типы доменных хуков — импорт из `@/hooks` рядом с хуками (без глубоких `@/hooks/use*` для типов). */
export type { RevenueHunterSavedResponse } from "./useRevenueHunter";
export type {
  WaitlistEntryRead,
  WaitlistEntry,
} from "./useAdminWaitlist";
export type { CreateAdminBookingPayload } from "./useAdminBookings";
export type { PatientAiInsightWithStatus } from "./useChatAi";
export type {
  CreateFinanceTransactionBody,
  FinanceLiabilityResponse,
  FinanceTransactionsFilters,
} from "./useErpFinance";
