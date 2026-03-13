/** Shared API response types aligned with backend DTOs */

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

export interface ChatMessageDto {
  id: string;
  sender_type: string;
  message_type?: string;
  body: string;
  sticker_key?: string | null;
  created_at: string;
  is_mine: boolean;
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
  status: "open" | "done";
  assigned_admin_id: string | null;
  assigned_admin_name: string | null;
  has_comment: boolean;
  last_comment_preview: string | null;
  conversation_id: string | null;
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
