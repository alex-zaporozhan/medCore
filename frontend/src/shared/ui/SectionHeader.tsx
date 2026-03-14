import { Group, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

interface SectionHeaderProps {
  overline?: string;
  title: string;
  description?: string;
  rightSlot?: ReactNode;
}

export function SectionHeader({ overline, title, description, rightSlot }: SectionHeaderProps) {
  return (
    <Group justify="space-between" align={description ? "flex-start" : "center"} mb="md">
      <Stack gap={4} style={{ maxWidth: "70%" }}>
        {overline && (
          <Text size="xs" fw={600} c="var(--text-muted)" tt="uppercase" lts={0.5}>
            {overline}
          </Text>
        )}
        <Title order={3} style={{ color: "var(--text-main)" }}>
          {title}
        </Title>
        {description && (
          <Text size="sm" c="dimmed">
            {description}
          </Text>
        )}
      </Stack>
      {rightSlot}
    </Group>
  );
}

