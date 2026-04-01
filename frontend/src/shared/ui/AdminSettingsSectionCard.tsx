import { Card, Stack, Text, type CardProps } from "@mantine/core";
import type { ReactNode } from "react";

/** DGN-P1-02 — единая оболочка секции настроек (касса, интеграции, AI и т.д.). */
export function AdminSettingsSectionCard({
  title,
  description,
  children,
  ...cardProps
}: Omit<CardProps, "children"> & {
  title: string;
  description?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <Card withBorder radius="md" p="md" className="data-table-card" {...cardProps}>
      <Stack gap="md">
        <Stack gap={description ? 4 : 0}>
          <Text fw={600} size="sm">
            {title}
          </Text>
          {description ? (
            <Text size="xs" c="dimmed" component="div">
              {description}
            </Text>
          ) : null}
        </Stack>
        {children}
      </Stack>
    </Card>
  );
}
