import { Badge, Tooltip } from "@mantine/core";
import type { AiFeatureStatus } from "@/shared/aiFeatures";
import { getAiFeatureBadgeColor, getAiFeatureStatusText, getAiFeatureTooltip } from "@/shared/aiFeatures";

export interface AiFeatureBadgeProps {
  status: AiFeatureStatus;
  size?: "xs" | "sm" | "md" | "lg";
  variant?: "light" | "filled" | "outline" | "dot" | "gradient" | "white" | "default" | "transparent";
}

/**
 * Standard AI feature status badge (stub / beta / prod) with tooltip (OMNI_UI_017 D3).
 */
export function AiFeatureBadge({ status, size = "xs", variant = "light" }: AiFeatureBadgeProps) {
  return (
    <Tooltip label={getAiFeatureTooltip(status)} withArrow>
      <Badge size={size} variant={variant} color={getAiFeatureBadgeColor(status)}>
        {getAiFeatureStatusText(status)}
      </Badge>
    </Tooltip>
  );
}
