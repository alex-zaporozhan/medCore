/**
 * AI Agent (Spotlight "Спросить AI"). Contract: POST /api/v1/ai/agent or similar.
 * Stub: returns static message until backend is ready.
 */

import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import { getAdminToken } from "@/api/client";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAiFeatures } from "@/shared/aiFeatures";

export interface AiAgentRequest {
  query: string;
}

export interface AiAgentResponse {
  answer: string;
}

export function useAiAgent() {
  const token = getAdminToken();
  const { currentClinicId } = useAdminClinic();
  const aiFeatures = useAiFeatures(currentClinicId ?? null);
  const spotlightFeature = aiFeatures.get("omni.spotlight.agent");

  return useMutation({
    mutationFn: async (body: AiAgentRequest): Promise<AiAgentResponse> => {
      const trimmed = body.query.trim();
      if (!trimmed) return { answer: "Введите вопрос." };

      if (spotlightFeature.status === "stub") {
        return {
          answer:
            "AI‑агент сейчас в режиме stub (демо): реальные вызовы отключены.\n\n" +
            "Ваш вопрос: «" +
            trimmed +
            "»\n\n" +
            "Подсказка: включите внешний AI‑провайдер в настройках (если доступно) или обратитесь к администратору.",
        };
      }
      try {
        const res = await api.post<AiAgentResponse>("/v1/ai/agent", { query: trimmed }, token);
        if (res?.answer) return res;
      } catch {
        // fallback to stub
      }
      return {
        answer:
          `AI‑агент временно недоступен (mode: ${spotlightFeature.status}). ` +
          "Попробуйте позже или используйте ручной сценарий.\n\n" +
          "Ваш вопрос: «" +
          trimmed +
          "».",
      };
    },
  });
}
