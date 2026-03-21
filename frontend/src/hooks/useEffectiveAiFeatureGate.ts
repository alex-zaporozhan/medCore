import { useMemo } from "react";
import { useAiFeatures, getAiFeatureTooltip, type AiFeatureConfig } from "@/shared/aiFeatures";
import { useAvailableAiTools } from "./useAvailableAiTools";

export interface EffectiveAiFeatureGate {
  feature: AiFeatureConfig;
  /** Backend tools (RBAC + registry) present for this clinic. */
  toolsOk: boolean;
  /** Feature not in stub AND (if gated) required tools available. */
  enabled: boolean;
  /** Human-readable reason when `enabled` is false. */
  disabledReason: string | null;
}

export type UseEffectiveAiFeatureGateOptions = {
  /**
   * When false, do not require `requiredToolIds` for `enabled` (Spotlight and other non-tool UI).
   * @default true
   */
  gateByTools?: boolean;
};

/**
 * Combines global AI feature flags (`/admin/ai-status`) with per-context tool availability
 * (`/admin/omni/available-tools`). Lives in `hooks/` to avoid `shared` → `hooks` dependency inversion.
 */
export function useEffectiveAiFeatureGate(
  clinicId: string | null,
  featureId: string,
  requiredToolIds: string[],
  options?: UseEffectiveAiFeatureGateOptions
): EffectiveAiFeatureGate {
  const gateByTools = options?.gateByTools !== false;
  const ai = useAiFeatures(clinicId);
  const tools = useAvailableAiTools(clinicId);
  const feature = ai.get(featureId);
  const missingTools = gateByTools && !tools.hasAll(requiredToolIds);
  const toolsOk = !missingTools;
  const enabled = feature.status !== "stub" && toolsOk;

  const disabledReason = useMemo(() => {
    if (feature.status === "stub") return getAiFeatureTooltip(feature.status);
    if (missingTools) return "Недостаточно прав или backend‑tool недоступен.";
    return null;
  }, [feature.status, missingTools]);

  return {
    feature,
    toolsOk,
    enabled,
    disabledReason,
  };
}
