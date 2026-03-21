import { api } from "@/api/client";

export type UiEventPayload = {
  event_name: string;
  clinic_id?: string | null;
  feature_id?: string | null;
  feature_status?: string | null;
  trace_id?: string | null;
  meta?: Record<string, unknown> | null;
};

export async function logUiEvent(payload: UiEventPayload): Promise<void> {
  try {
    await api.post<{ status: string }>("/v1/admin/ui-events", payload);
  } catch {
    // telemetry must never break UX
  }
}

