import { Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

/**
 * Оболочка вкладок правого инспектора (Omni Chat и др.): заголовок + лид + тело.
 * Единый коммерческий ритм типографики и отступов.
 */
export function OmniInspectorTabShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Stack gap="sm">
      <Stack gap={4}>
        <Text size="sm" fw={600}>
          {title}
        </Text>
        {description ? (
          <Text size="xs" c="dimmed">
            {description}
          </Text>
        ) : null}
      </Stack>
      {children}
    </Stack>
  );
}

export function OmniInspectorSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Stack gap="xs">
      <Text size="xs" fw={600}>
        {title}
      </Text>
      {children}
    </Stack>
  );
}
