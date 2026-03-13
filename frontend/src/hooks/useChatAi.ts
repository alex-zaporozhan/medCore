import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ConversationSummary, SuggestReplyResult, PatientAiInsight } from "@/api/types";

export type AiStatus = "unknown" | "disabled" | "fallback_local" | "external_active";

export interface ConversationSummaryWithStatus {
  summary: string;
  aiStatus: AiStatus;
}

export interface SuggestReplyWithStatus {
  variants: string[];
  aiStatus: AiStatus;
}

export interface PatientAiInsightWithStatus {
  summary: string;
  risk_flags: string[];
  next_best_action?: string | null;
  aiStatus: AiStatus;
}

function normalizeAiStatus(raw?: string | null): AiStatus {
  if (raw === "disabled" || raw === "fallback_local" || raw === "external_active") {
    return raw;
  }
  return "unknown";
}

export function useConversationSummary(conversationId: string | null) {
  return useMutation({
    mutationFn: async (): Promise<ConversationSummaryWithStatus> => {
      if (!conversationId) {
        throw new Error("Нет выбранного диалога");
      }
      const raw = await api.post<ConversationSummary & { ai_status?: string | null }>(
        `/v1/admin/chat/conversations/${conversationId}/ai-summary`
      );
      return {
        summary: raw.summary,
        aiStatus: normalizeAiStatus((raw as any).ai_status),
      };
    },
  });
}

export function useSuggestReply(conversationId: string | null) {
  return useMutation({
    mutationFn: async (intent?: string | null): Promise<SuggestReplyWithStatus> => {
      if (!conversationId) {
        throw new Error("Нет выбранного диалога");
      }
      const body = intent ? { intent } : {};
      const raw = await api.post<SuggestReplyResult & { ai_status?: string | null }>(
        `/v1/admin/chat/conversations/${conversationId}/ai-suggest-reply`,
        body
      );
      return {
        variants: raw.variants ?? [],
        aiStatus: normalizeAiStatus((raw as any).ai_status),
      };
    },
  });
}

export function usePatientAiInsight(patientId: string | null) {
  return useMutation({
    mutationFn: async (): Promise<PatientAiInsightWithStatus> => {
      if (!patientId) {
        throw new Error("Нет выбранного пациента");
      }
      const raw = await api.get<PatientAiInsight & { ai_status?: string | null }>(
        `/v1/admin/patients/${patientId}/ai-insight`
      );
      return {
        summary: raw.summary,
        risk_flags: raw.risk_flags,
        next_best_action: raw.next_best_action,
        aiStatus: normalizeAiStatus((raw as any).ai_status),
      };
    },
  });
}
