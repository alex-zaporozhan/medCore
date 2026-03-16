import { Grid, Skeleton, Stack } from "@mantine/core";

export interface PageSkeletonProps {
  /** "table" = header row + data rows; "cards" = card grid */
  variant?: "table" | "cards";
  /** Number of table rows (default 6) */
  rows?: number;
  /** Number of card placeholders (default 4) */
  cardsCount?: number;
}

/**
 * Page-level skeleton for list/table or cards. No Loader/spinner.
 * Use when isLoading for tables/lists (REV: Skeleton by contour).
 */
export function PageSkeleton({
  variant = "table",
  rows = 6,
  cardsCount = 4,
}: PageSkeletonProps) {
  if (variant === "cards") {
    return (
      <Grid>
        {Array.from({ length: cardsCount }).map((_, i) => (
          <Grid.Col key={i} span={{ base: 12, sm: 6, md: 4 }}>
            <Skeleton height={120} radius="md" />
          </Grid.Col>
        ))}
      </Grid>
    );
  }

  const colCount = 4;
  return (
    <Stack gap="sm">
      {/* Header row */}
      <Stack gap="xs" style={{ flexDirection: "row", flexWrap: "nowrap" }}>
        {Array.from({ length: colCount }).map((_, i) => (
          <Skeleton key={i} height={24} radius="xs" style={{ flex: 1, maxWidth: i === colCount - 1 ? 80 : undefined }} />
        ))}
      </Stack>
      {/* Data rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <Stack key={i} gap="xs" style={{ flexDirection: "row", flexWrap: "nowrap" }}>
          {Array.from({ length: colCount }).map((_, j) => (
            <Skeleton
              key={j}
              height={20}
              radius="xs"
              style={{ flex: 1, maxWidth: j === colCount - 1 ? 60 : undefined }}
            />
          ))}
        </Stack>
      ))}
    </Stack>
  );
}
