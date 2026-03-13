import { Stack, Text } from "@mantine/core";

interface EmptyStateHintProps {
  title: string;
  subtitle?: string;
}

export function EmptyStateHint({ title, subtitle }: EmptyStateHintProps) {
  return (
    <Stack gap="xs" py="md">
      <Text size="md" fw={500}>
        {title}
      </Text>
      {subtitle && (
        <Text size="sm" c="dimmed">
          {subtitle}
        </Text>
      )}
    </Stack>
  );
}
