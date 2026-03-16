/**
 * AI Agent (Spotlight "Спросить AI"). Contract: POST /api/v1/ai/agent or similar.
 * Stub: returns static message until backend is ready.
 */

import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import { getAdminToken } from "@/api/client";

export interface AiAgentRequest {
  query: string;
}

export interface AiAgentResponse {
  answer: string;
}

export function useAiAgent() {
  const token = getAdminToken();
  return useMutation({
    mutationFn: async (body: AiAgentRequest): Promise<AiAgentResponse> => {
      try {
        const res = await api.post<AiAgentResponse>("/v1/ai/agent", body, token);
        if (res?.answer) return res;
      } catch {
        // fallback to stub
      }
      return {
        answer:
          "Сервис AI-ассистента пока настраивается. Ваш вопрос: «" +
          body.query +
          "». Обратитесь к администратору для подключения.",
      };
    },
  });
}
