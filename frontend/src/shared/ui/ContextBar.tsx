import { Group, Title } from "@mantine/core";
import type { ReactNode } from "react";

interface ContextBarProps {
  title: string;
  /** Breadcrumbs or extra text to the right of title (optional) */
  breadcrumbs?: ReactNode;
  /** Main action buttons on the right */
  actions?: ReactNode;
}

/**
 * Context Bar for admin pages: one row with page title (left) and action buttons (right).
 * Use at the top of each admin page content (admin shell / context bar pattern).
 */
export function ContextBar({ title, breadcrumbs, actions }: ContextBarProps) {
  return (
    <Group justify="space-between" mb="md" wrap="nowrap">
      <Group gap="sm" wrap="nowrap">
        <Title order={3}>{title}</Title>
        {breadcrumbs}
      </Group>
      {actions != null && <Group gap="xs">{actions}</Group>}
    </Group>
  );
}
