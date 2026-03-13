import { Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
}

/**
 * Empty state with optional icon and muted text (--text-muted).
 * Replaces or complements EmptyStateHint with consistent styling.
 */
export function EmptyState({ title, subtitle, icon }: EmptyStateProps) {
  return (
    <Stack gap="xs" py="md" align="center">
      {icon}
      <Text size="md" fw={500} c="var(--text-main)">
        {title}
      </Text>
      {subtitle && (
        <Text size="sm" c="dimmed" style={{ color: "var(--text-muted)" }}>
          {subtitle}
        </Text>
      )}
    </Stack>
  );
}
