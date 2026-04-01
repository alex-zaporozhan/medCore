/** Shared API response types aligned with backend DTOs */

/**
 * Тело ошибки FastAPI/HTTPException в JSON — техпаспорт §3 (`client.ts` разбор).
 * `detail` — строка, объект бизнес-ошибки, **массив** (часто 422 validation), или реже `string[]`.
 */
export interface ApiErrorDetailObject {
  message?: string;
  code?: string;
  trace_id?: string;
  details?: Record<string, unknown>;
}

/** Элемент `detail[]` при 422 (FastAPI validation). */
export interface ApiValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export interface ApiErrorResponseBody {
  detail?: string | ApiErrorDetailObject | ApiValidationErrorItem[] | string[];
  /** Редко сверх `detail`; учитывается, если из `detail` не извлечено сообщение */
  message?: string;
  code?: string;
}

export const SPECIALIST_ROLE_OPTIONS = [
  { value: "doctor", label: "Врач" },
  { value: "nurse", label: "Медсестра" },
  { value: "master", label: "Мастер" },
  { value: "therapist", label: "Терапевт" },
  { value: "barber", label: "Барбер" },
  { value: "stylist", label: "Стилист" },
  { value: "nail_master", label: "Мастер маникюра" },
  { value: "pedicure_master", label: "Мастер педикюра" },
  { value: "massage_therapist", label: "Массажист" },
  { value: "other", label: "Другое" },
] as const;

export type SpecialistRole = (typeof SPECIALIST_ROLE_OPTIONS)[number]["value"];

export interface Doctor {
  id: string;
  clinic_id: string;
  full_name: string;
  specialization: string;
  photo_url: string | null;
  rating: string;
  experience_years: number | null;
  is_active: boolean;
  specialist_role?: string;
  specialist_role_custom_name?: string | null;
  display_role?: string;
}

export const BUSINESS_TYPE_OPTIONS = [
  { value: "stomatology", label: "Стоматология" },
  { value: "clinic", label: "Клиника" },
  { value: "beauty_salon", label: "Салон красоты" },
  { value: "barbershop", label: "Барбершоп" },
  { value: "nail_salon", label: "Салон маникюра" },
  { value: "massage_salon", label: "Массажный салон" },
  { value: "other", label: "Другое" },
] as const;

export type BusinessType = (typeof BUSINESS_TYPE_OPTIONS)[number]["value"];

export interface BusinessLexicon {
  business_type: string;
  business_type_custom_name?: string | null;
  person_label_singular: string;
  person_label_plural: string;
  staff_label_plural: string;
  role_display: Record<string, string>;
}

export interface PaymentOption {
  gateway_id: string;
  display_name: string;
}

export interface Clinic {
  id: string;
  clinic_slug?: string | null;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  workday_start: string;
  workday_end: string;
  slot_duration_minutes: number;
  prepayment_amount: string;
  prepayment_enabled?: boolean;
  payment_gateway?: string;
  payment_gateway_custom_name?: string | null;
  payment_options?: PaymentOption[];
  yookassa_shop_id?: string | null;
  theme_primary_color?: string | null;
  theme_logo_url?: string | null;
  theme_font_family?: string | null;
  business_type?: string;
  business_type_custom_name?: string | null;
  person_label_singular?: string | null;
  person_label_plural?: string | null;
  staff_label_plural?: string | null;
  business_lexicon?: BusinessLexicon;
}

export interface PublicDoctorProfile {
  id: string;
  clinic_id: string;
  doctor_id: string;
  doctor_slug: string;
  is_published: boolean;
  public_photo_url: string | null;
  short_bio: string | null;
  about_md: string | null;
  languages?: Record<string, unknown> | null;
  education?: Record<string, unknown> | null;
  certifications?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface PublicDoctorProfilePublicDto {
  clinic_id: string;
  clinic_slug: string;
  doctor_id: string;
  doctor_slug: string;
  doctor_full_name: string;
  doctor_specialization: string;
  doctor_photo_url: string | null;
  doctor_display_role?: string | null;
  public_photo_url: string | null;
  short_bio: string | null;
  about_md: string | null;
  languages?: Record<string, unknown> | null;
  education?: Record<string, unknown> | null;
  certifications?: Record<string, unknown> | null;
}

export interface Service {
  id: string;
  clinic_id: string;
  name: string;
  category: string;
  description?: string | null;
  price: string;
  duration_minutes?: number;
  is_active: boolean;
  base_price?: string;
  effective_price?: string;
  has_active_discount?: boolean;
  discount_id?: string | null;
  discount_type?: string | null;
  discount_label?: string | null;
}

export interface ServiceDoctorLink {
  doctor_id: string;
  custom_price: string | null;
  is_active: boolean;
}

export interface AdminServiceRead {
  service: Service;
  doctors: ServiceDoctorLink[];
}

export interface PublicService {
  id: string;
  clinic_id: string;
  name: string;
  category: string;
  description: string | null;
  price: string;
  duration_minutes: number;
  is_active: boolean;
  doctor_ids: string[];
  base_price?: string;
  effective_price?: string;
  has_active_discount?: boolean;
  discount_id?: string | null;
  discount_type?: string | null;
  discount_label?: string | null;
}

export interface Patient {
  id: string;
  clinic_id: string;
  phone: string;
  full_name: string | null;
  email: string | null;
}

export interface ScheduleSlot {
  start_time: string;
  end_time: string;
  is_available: boolean;
  booking_id: string | null;
  status: string | null;
}

export interface DailySchedule {
  doctor_id: string;
  date: string;
  slots: ScheduleSlot[];
}

export interface DoctorSlot {
  start_time: string;
  end_time: string;
  is_available: boolean;
  booking_id: string | null;
  status: string | null;
}

export interface AggregatedSchedule {
  doctors: string[];
  date: string;
  times: string[];
  by_doctor: Record<string, DoctorSlot[]>;
}

export interface Booking {
  id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string;
  service_id: string;
  appointment_date: string;
  appointment_time: string;
  status: string;
  prepayment_amount: string;
  payment_id: string | null;
  notes: string | null;
  /** Заполняется в GET /v1/admin/bookings для отображения ФИО/названий */
  patient_name?: string | null;
  doctor_name?: string | null;
  service_name?: string | null;
}

// ERP finance

export interface Cashbox {
  id: string;
  clinic_id: string;
  name: string;
  type: string;
  currency: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  balance?: string | null;
}

export interface FinancialTransaction {
  id: string;
  clinic_id: string;
  cashbox_id: string;
  type: string;
  amount: string;
  currency: string;
  happened_at: string;
  description: string | null;
  booking_id: string | null;
  payment_id: string | null;
  source: string;
  created_at: string;
  updated_at: string;
}

// ERP payroll

export interface PayrollPolicy {
  id: string;
  clinic_id: string;
  doctor_id: string | null;
  role: string | null;
  fixed_per_shift: string;
  percent_from_services: string;
  percent_from_products: string;
  created_at: string;
  updated_at: string;
}

export interface SalaryTransaction {
  id: string;
  clinic_id: string;
  doctor_id: string;
  booking_id: string | null;
  amount: string;
  type: string;
  period_start: string | null;
  period_end: string | null;
  description: string | null;
  created_at: string;
}

// ERP inventory

export interface InventoryProduct {
  id: string;
  clinic_id: string;
  sku: string | null;
  name: string;
  unit: string;
  is_active: boolean;
}

export interface Warehouse {
  id: string;
  clinic_id: string;
  name: string;
  is_default: boolean;
}

export interface ServiceConsumable {
  id: string;
  clinic_id: string;
  service_id: string;
  product_id: string;
  quantity_per_service: string;
  unit: string;
}

export interface InventoryTransaction {
  id: string;
  clinic_id: string;
  warehouse_id: string;
  product_id: string;
  type: string;
  quantity: string;
  happened_at: string;
  description: string | null;
  booking_id: string | null;
}

export interface InventoryStockItem {
  product_id: string;
  warehouse_id: string;
  quantity: string;
  unit: string;
}

export interface DashboardReport {
  date: string;
  bookings_pending: number;
  bookings_confirmed: number;
  bookings_completed: number;
  bookings_cancelled: number;
  bookings_no_show: number;
  new_patients: number;
  revenue: string;
}

export interface NoShowReport {
  date_from: string;
  date_to: string;
  total: number;
  no_show_count: number;
  no_show_rate: number;
}

export interface RevenuePoint {
  date: string;
  amount: string;
}

export interface RevenueReport {
  date_from: string;
  date_to: string;
  total_revenue: string;
  points: RevenuePoint[];
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  patient_id: string;
}

export interface CreatePaymentResponse {
  payment_url: string;
  provider_payment_id?: string;
  /** When false, no redirect to YooKassa — booking is already confirmed. */
  prepayment_required?: boolean;
}

export interface ChatAttachmentBriefDto {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
}

export interface ChatMessageDto {
  id: string;
  sender_type: string;
  message_type?: string;
  body: string;
  sticker_key?: string | null;
  created_at: string;
  is_mine: boolean;
  attachments?: ChatAttachmentBriefDto[];
}

export interface ConversationResponse {
  conversation_id: string;
  unread_by_patient_count: number;
  unread_by_admin_count: number;
  last_message_at: string | null;
}

export interface MessagesResponse {
  items: ChatMessageDto[];
  next_cursor: string | null;
}

export interface AdminConversationListItemDto {
  conversation_id: string;
  patient_id: string;
  patient_name: string | null;
  patient_phone: string;
  assigned_admin_id: string | null;
  assigned_admin_name: string | null;
  last_message_at: string | null;
  last_message_sender_type: string | null;
  unread_by_admin_count: number;
}

export interface AdminConversationsResponse {
  items: AdminConversationListItemDto[];
  total: number;
}

export interface SendMessageRequest {
  message_type?: string;
  body?: string;
  sticker_key?: string | null;
}

export interface MarkReadRequest {
  up_to_message_id?: string | null;
}

export interface AssignRequest {
  admin_id?: string | null;
}

export interface AssignResponse {
  conversation_id: string;
  assigned_admin_id: string | null;
}

export interface AttentionItem {
  id: string;
  clinic_id: string;
  patient_id: string;
  kind: "follow_up" | "retention_gap" | "conflict";
  title: string;
  description: string;
  priority: number;
  due_at: string | null;
  created_at: string;
  updated_at: string;
  patient_full_name: string | null;
  patient_phone: string;
  patient_tags: string[];
  status: "new" | "in_progress" | "resolved" | "archived";
  assigned_admin_id: string | null;
  assigned_admin_name: string | null;
  has_comment: boolean;
  last_comment_preview: string | null;
  conversation_id: string | null;
  tasks_total: number;
  tasks_open: number;
  tasks_in_progress: number;
  tasks_done: number;
  tasks_cancelled: number;
}

export interface AttentionFeed {
  follow_up: AttentionItem[];
  retention_gap: AttentionItem[];
  conflicts: AttentionItem[];
}

export interface ConversationSummary {
  summary: string;
}

export interface SuggestReplyResult {
  variants: string[];
}

export interface PatientAiInsight {
  summary: string;
  risk_flags: string[];
  next_best_action?: string | null;
}

// Loyalty & subscriptions

export interface SubscriptionPackage {
  id: string;
  clinic_id: string;
  code: string;
  name: string;
  description?: string | null;
  kind: string;
  services_included: string[];
  total_visits?: number | null;
  total_amount?: string | null;
  price: string;
  validity_days?: number | null;
  is_active: boolean;
}

export interface CustomerSubscription {
  id: string;
  clinic_id: string;
  patient_id: string;
  subscription_package_id: string;
  status: string;
  purchased_at: string;
  activated_at?: string | null;
  expires_at?: string | null;
  remaining_visits?: number | null;
  remaining_amount?: string | null;
  payment_id?: string | null;
  notes?: string | null;
}

export interface Wallet {
  id: string;
  clinic_id: string;
  patient_id: string;
  balance: string;
  currency: string;
  updated_at: string;
}

export interface WalletTransaction {
  id: string;
  clinic_id: string;
  wallet_id: string;
  type: string;
  amount: string;
  happened_at: string;
  booking_id?: string | null;
  subscription_id?: string | null;
  description?: string | null;
}

export interface PatientLoyaltyMeResponse {
  subscriptions: CustomerSubscription[];
  wallet: Wallet | null;
  wallet_transactions: WalletTransaction[];
}

export interface PatientLoyaltyHistoryItem {
  kind: string;
  happened_at: string;
  details: Record<string, unknown>;
}

export interface PatientLoyaltyHistoryResponse {
  items: PatientLoyaltyHistoryItem[];
}

export interface AdminLoyaltySummaryByContactResponse {
  patient_id: string | null;
  patient_full_name: string | null;
  patient_phone: string | null;
  subscriptions: CustomerSubscription[];
  wallet: Wallet | null;
  wallet_transactions: WalletTransaction[];
}

/** LOY_AI_014: per-clinic loyalty campaign automation */
export interface LoyaltyCampaignSettings {
  clinic_id: string;
  expiring_packages_enabled: boolean;
  high_balance_low_activity_enabled: boolean;
  reengagement_enabled: boolean;
  channel_tasks_enabled: boolean;
  channel_omnichannel_enabled: boolean;
  /** Skip expiring Task if SMS expiring notification already sent today (same subscription). */
  skip_expiring_task_if_sms_expiring_sent_today: boolean;
  max_contacts_per_day_clinic: number;
  max_contacts_per_day_patient: number;
  campaign_cooldown_days: number;
  reengagement_inactive_days: number;
  /** Max LOYALTY_* tasks per patient in current calendar month (UTC). */
  max_campaign_touches_per_patient_month: number;
  updated_at?: string | null;
}

export interface LoyaltyCampaignRunResult {
  clinic_id: string;
  created_expiring: number;
  created_high_balance: number;
  created_reengagement: number;
  skipped_limits: number;
  skipped_cooldown: number;
  skipped_cross_campaign: number;
  skipped_sms_duplicate: number;
  skipped_opt_out: number;
}

// Paperless Office: digital forms

export interface DigitalFormFieldSchema {
  id: string;
  label: string;
  type: string;
  required: boolean;
  options?: string[];
  sensitive: boolean;
}

export interface DigitalFormTemplateSchema {
  fields: DigitalFormFieldSchema[];
}

export type FormInstanceStatus =
  | "draft"
  | "issued"
  | "in_progress"
  | "signed"
  | "cancelled"
  | "expired"
  | "revoked"
  | "unknown";

export interface DigitalFormTemplate {
  id: string;
  clinic_id: string;
  code: string;
  name: string;
  description: string | null;
  version: number;
  schema: DigitalFormTemplateSchema;
  requires_signature: boolean;
  /** @deprecated optional only during rollout; API always sends boolean after PPR-2 migration */
  required_for_visit_completion?: boolean;
  active: boolean;
}

export interface DigitalFormSubmission {
  id: string;
  clinic_id: string;
  template_id: string;
  patient_id: string | null;
  booking_id: string | null;
  status: FormInstanceStatus;
  submitted_at: string | null;
  signed_at: string | null;
  expires_at: string | null;
  submitted_by: string;
  data: Record<string, unknown>;
  signature_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DigitalFormSubmissionListItem extends DigitalFormSubmission {
  template_code: string;
  template_name: string;
}

export interface ESignatureRead {
  id: string;
  clinic_id: string;
  patient_id: string | null;
  digital_form_submission_id: string;
  signed_at: string;
  signer_name: string | null;
  signer_role: string;
  signature_type: string;
  signature_payload: Record<string, unknown>;
  meta: Record<string, unknown> | null;
}

export interface DigitalFormSubmissionWithTemplateAndSignature {
  submission: DigitalFormSubmission;
  template: DigitalFormTemplate;
  signature: ESignatureRead | null;
}
