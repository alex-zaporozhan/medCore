import { Button, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  /** Alias for subtitle (Premium Empty State) */
  description?: string;
  subtitle?: string;
  /** Optional icon, size 64, dimmed (e.g. IconInbox size={64} stroke={1} color="var(--mantine-color-gray-4)") */
  icon?: ReactNode;
  /** Single CTA button (e.g. "Создать задачу") */
  action?: { label: string; onClick: () => void };
}

/**
 * Empty state with optional icon and muted text.
 * Premium Empty State: icon + title + description + one CTA button.
 * Backward compatible: without action/icon works as before.
 */
export function EmptyState({ title, description, subtitle, icon, action }: EmptyStateProps) {
  const desc = description ?? subtitle;
  return (
    <Stack gap="xs" py="xl" align="center">
      {icon}
      <Text size="md" fw={600} c="var(--text-main)">
        {title}
      </Text>
      {desc && (
        <Text size="sm" c="dimmed" style={{ color: "var(--text-muted)" }}>
          {desc}
        </Text>
      )}
      {action && (
        <Button variant="light" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </Stack>
  );
}
