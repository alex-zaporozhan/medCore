import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/** Техдолг (техпаспорт §4): `useAiFeatures` — хук TanStack Query; целевое место — `hooks/`, реэкспорт из `@/hooks` (отдельный эпик, без смены контракта). */

export type AiFeatureStatus = "stub" | "beta" | "prod";

export interface AiFeatureConfig {
  id: string;
  label: string;
  status: AiFeatureStatus;
  description?: string;
}

type AiStatusResponse = {
  ai_mode: "disabled" | "fallback_local" | "external_active";
  features: Record<string, boolean>;
};

const DEFAULT_FEATURES: Record<string, AiFeatureConfig> = {
  "omni.spotlight.agent": {
    id: "omni.spotlight.agent",
    label: "Spotlight AI‑агент",
    status: "stub",
    description:
      "Быстрый вопрос ассистенту из Spotlight. В режиме stub отвечает демо‑сообщением без вызовов backend/tools.",
  },
  "omni.tools.suggest_slots": {
    id: "omni.tools.suggest_slots",
    label: "Подбор слотов записи",
    status: "stub",
    description:
      "Подсказка доступных слотов/окон. Пока скрыто/отключено до готовности backend‑интеграций.",
  },
  "omni.tools.crm_suggest_next_stage": {
    id: "omni.tools.crm_suggest_next_stage",
    label: "CRM: следующая стадия лида",
    status: "beta",
    description:
      "AI‑рекомендации по стадии лида. Может требовать внешнего AI‑провайдера и быть недоступно локально.",
  },
  "omni.tools.create_task": {
    id: "omni.tools.create_task",
    label: "Создание задачи (AI/Omni контекст)",
    status: "beta",
    description:
      "Создание задачи из AI‑рекомендации/контекста. В stub‑режиме реальные мутации отключены.",
  },
};

export function getDefaultAiFeatures(): AiFeatureConfig[] {
  return Object.values(DEFAULT_FEATURES);
}

export function getAiFeatureStatusText(status: AiFeatureStatus): string {
  if (status === "prod") return "prod";
  if (status === "beta") return "beta";
  return "stub";
}

export function getAiFeatureBadgeColor(status: AiFeatureStatus): string {
  if (status === "prod") return "green";
  /** Beta AI — палитра `ai` (Midnight канон) */
  if (status === "beta") return "ai";
  return "gray";
}

export function getAiFeatureTooltip(status: AiFeatureStatus): string {
  if (status === "prod") return "Функция активна в production‑режиме.";
  if (status === "beta")
    return "Beta: функция активна, но могут быть ошибки и ограничения. При сбоях используйте ручной сценарий.";
  return "Stub/демо: функция в разработке. Реальные вызовы backend/tools отключены.";
}

function mergeWithAiStatus(
  defaults: Record<string, AiFeatureConfig>,
  aiStatus: AiStatusResponse | null
): Record<string, AiFeatureConfig> {
  const merged: Record<string, AiFeatureConfig> = { ...defaults };

  // If external AI is configured globally — we can treat some features as beta/prod.
  if (aiStatus?.ai_mode === "external_active") {
    merged["omni.spotlight.agent"] = {
      ...merged["omni.spotlight.agent"],
      status: merged["omni.spotlight.agent"]?.status === "stub" ? "beta" : merged["omni.spotlight.agent"].status,
    };
  }

  // If AI is explicitly disabled globally, keep Spotlight in stub.
  if (aiStatus?.ai_mode === "disabled") {
    merged["omni.spotlight.agent"] = {
      ...merged["omni.spotlight.agent"],
      status: "stub",
    };
  }

  // Per-feature toggles from backend (keys must match DEFAULT_FEATURES ids when present).
  if (aiStatus?.features) {
    for (const [fid, flag] of Object.entries(aiStatus.features)) {
      if (fid in merged) {
        const cur = merged[fid];
        merged[fid] = {
          ...cur,
          status: flag ? "prod" : "stub",
        };
      }
    }
  }

  return merged;
}

export function useAiFeatures(clinicId: string | null) {
  const aiStatusQuery = useQuery({
    queryKey: ["admin-ai-status"],
    queryFn: () => api.get<AiStatusResponse>("/v1/admin/ai-status"),
    staleTime: 60_000,
    retry: 0,
  });

  const featuresById = useMemo(() => {
    const defaults = DEFAULT_FEATURES;
    const status = aiStatusQuery.data ?? null;
    return mergeWithAiStatus(defaults, status);
  }, [aiStatusQuery.data]);

  const list = useMemo(() => Object.values(featuresById), [featuresById]);

  const get = useMemo(() => {
    return (id: string): AiFeatureConfig => {
      return featuresById[id] ?? { id, label: id, status: "stub" };
    };
  }, [featuresById]);

  // keep clinicId in signature for future per-clinic overrides; currently unused
  void clinicId;

  return {
    isLoading: aiStatusQuery.isLoading,
    isError: aiStatusQuery.isError,
    error: aiStatusQuery.error,
    list,
    featuresById,
    get,
  };
}

