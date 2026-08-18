import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import i18n from "@/i18n";

/** Техдолг: `useAiFeatures` — хук TanStack Query; целевое место — `hooks/`, реэкспорт из `@/hooks` (отдельная задача, без смены контракта). */

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

function defaultAiFeaturesById(): Record<string, AiFeatureConfig> {
  return {
    "omni.spotlight.agent": {
      id: "omni.spotlight.agent",
      label: i18n.t("ai.features.spotlightAgent.label"),
      status: "stub",
      description: i18n.t("ai.features.spotlightAgent.description"),
    },
    "omni.tools.suggest_slots": {
      id: "omni.tools.suggest_slots",
      label: i18n.t("ai.features.suggestSlots.label"),
      status: "stub",
      description: i18n.t("ai.features.suggestSlots.description"),
    },
    "omni.tools.crm_suggest_next_stage": {
      id: "omni.tools.crm_suggest_next_stage",
      label: i18n.t("ai.features.crmNextStage.label"),
      status: "beta",
      description: i18n.t("ai.features.crmNextStage.description"),
    },
    "omni.tools.create_task": {
      id: "omni.tools.create_task",
      label: i18n.t("ai.features.createTask.label"),
      status: "beta",
      description: i18n.t("ai.features.createTask.description"),
    },
  };
}

export function getDefaultAiFeatures(): AiFeatureConfig[] {
  return Object.values(defaultAiFeaturesById());
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
  return i18n.t(`ai.tooltip.${status}`);
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
    const defaults = defaultAiFeaturesById();
    const status = aiStatusQuery.data ?? null;
    return mergeWithAiStatus(defaults, status);
  }, [aiStatusQuery.data, i18n.language]);

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

