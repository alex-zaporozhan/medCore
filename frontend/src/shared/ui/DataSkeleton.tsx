import { Skeleton, Stack } from "@mantine/core";

interface DataSkeletonProps {
  /** Number of line placeholders (for list/table loading) */
  lines?: number;
  /** Use card-style block instead of lines */
  card?: boolean;
}

export function DataSkeleton({ lines = 5, card }: DataSkeletonProps) {
  if (card) {
    return (
      <Skeleton height={120} radius="md" />
    );
  }
  return (
    <Stack gap="sm">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={24} radius="xs" width={i === lines - 1 && lines > 1 ? "70%" : undefined} />
      ))}
    </Stack>
  );
}
