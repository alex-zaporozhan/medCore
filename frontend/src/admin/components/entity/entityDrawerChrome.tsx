import { Box, Group, Paper, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

/** Section label in entity drawers — DGN-P0-03 (shared contract). */
export function EntityDrawerSectionTitle({ children }: { children: ReactNode }) {
  return (
    <Text size="xs" tt="uppercase" fw={600} c="dimmed">
      {children}
    </Text>
  );
}

/**
 * Одно поле в карточке сущности — Swiss Slate / Ink §3.6 (`DESIGN_TOKENS_85_PLUS` surface.cardSoft).
 * Используется в модалках/дроверах для сходимости с playbook Step 4 (drawer/modal convergence).
 */
export function EntityDrawerFieldBlock({
  label,
  children,
}: {
  label: ReactNode;
  children: ReactNode;
}) {
  return (
    <Paper
      p="sm"
      radius="md"
      withBorder
      bg="white"
      style={{
        borderColor: "var(--mantine-color-gray-1)",
        boxShadow: "0 1px 2px rgba(15, 20, 25, 0.04)",
      }}
    >
      <Stack gap={6}>
        {typeof label === "string" ? (
          <EntityDrawerSectionTitle>{label}</EntityDrawerSectionTitle>
        ) : (
          label
        )}
        <Box>{children}</Box>
      </Stack>
    </Paper>
  );
}

/** Sticky-style footer actions — §3.6.11 mirror of modal primary row. */
export function EntityDrawerFooterBar({ children }: { children: ReactNode }) {
  return (
    <Group
      justify="flex-end"
      gap="sm"
      pt="md"
      mt="md"
      style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}
    >
      {children}
    </Group>
  );
}
