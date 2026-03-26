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
    <Group
      justify="space-between"
      mb="md"
      wrap="nowrap"
      className="glass-light"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 5,
        marginInline: "calc(-1 * var(--mantine-spacing-md))",
        paddingInline: "var(--mantine-spacing-md)",
        paddingTop: "var(--mantine-spacing-xs)",
        paddingBottom: "var(--mantine-spacing-sm)",
        marginTop: "calc(-1 * var(--mantine-spacing-sm))",
      }}
    >
      <Group gap="sm" wrap="nowrap">
        <Title order={3}>{title}</Title>
        {breadcrumbs}
      </Group>
      {actions != null && <Group gap="xs">{actions}</Group>}
    </Group>
  );
}
