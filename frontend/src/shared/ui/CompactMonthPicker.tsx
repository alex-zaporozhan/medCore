import { useMemo } from "react";
import type { CSSProperties } from "react";
import { ActionIcon, Box, Button, Group, SimpleGrid, Text } from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import dayjs from "dayjs";
import "dayjs/locale/ru";

dayjs.locale("ru");

export type CompactMonthPickerSize = "compact" | "comfortable";

export interface CompactMonthPickerProps {
  value: string;
  onChange: (iso: string) => void;
  monthAnchor: dayjs.Dayjs;
  onMonthAnchorChange: (d: dayjs.Dayjs) => void;
  size?: CompactMonthPickerSize;
  /** Обёртка с фоном и рамкой (как в модалке «Новое событие») */
  withShell?: boolean;
  className?: string;
  style?: CSSProperties;
}

function buildMonthCells(monthAnchor: dayjs.Dayjs) {
  const monthStart = monthAnchor.startOf("month");
  const mondayBasedDow = (monthStart.day() + 6) % 7;
  const gridStart = monthStart.subtract(mondayBasedDow, "day");
  return Array.from({ length: 42 }, (_, i) => gridStart.add(i, "day"));
}

/**
 * Компактный месячный календарь (Пн–Вс), тот же паттерн, что на /admin/calendar → «Новое событие».
 */
export function CompactMonthPicker({
  value,
  onChange,
  monthAnchor,
  onMonthAnchorChange,
  size = "compact",
  withShell = true,
  className,
  style,
}: CompactMonthPickerProps) {
  const cells = useMemo(() => buildMonthCells(monthAnchor), [monthAnchor]);
  const isCompact = size === "compact";
  const btnSize = "xs" as const;
  const headSize = isCompact ? "10px" : "xs";
  const iconSz = isCompact ? 16 : 18;
  const pad = isCompact ? "var(--space-8)" : "var(--space-10)";
  const gap = isCompact ? 2 : 4;

  const inner = (
    <>
      <Group justify="space-between" align="center" gap={4} wrap="nowrap">
        <ActionIcon
          variant="subtle"
          size={isCompact ? "md" : "lg"}
          radius="md"
          onClick={() => onMonthAnchorChange(monthAnchor.subtract(1, "month"))}
          aria-label="Предыдущий месяц"
          style={{ background: "var(--bg-card)", boxShadow: "var(--shadow-soft-sm)", flexShrink: 0 }}
        >
          <IconChevronLeft size={iconSz} stroke={1.5} />
        </ActionIcon>
        <Text
          size={isCompact ? "xs" : "sm"}
          fw={800}
          style={{ textAlign: "center", lineHeight: 1.25, flex: 1, minWidth: 0 }}
        >
          {monthAnchor.format("MMMM YYYY")}
        </Text>
        <ActionIcon
          variant="subtle"
          size={isCompact ? "md" : "lg"}
          radius="md"
          onClick={() => onMonthAnchorChange(monthAnchor.add(1, "month"))}
          aria-label="Следующий месяц"
          style={{ background: "var(--bg-card)", boxShadow: "var(--shadow-soft-sm)", flexShrink: 0 }}
        >
          <IconChevronRight size={iconSz} stroke={1.5} />
        </ActionIcon>
      </Group>

      <SimpleGrid cols={7} spacing={gap} mt={isCompact ? 6 : 8}>
        {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((w) => (
          <Text key={w} size={headSize} fw={800} c="dimmed" style={{ textAlign: "center" }}>
            {w}
          </Text>
        ))}
      </SimpleGrid>

      <SimpleGrid cols={7} spacing={gap} mt={gap}>
        {cells.map((d) => {
          const iso = d.format("YYYY-MM-DD");
          const isSel = iso === value;
          const isThisMonth = d.month() === monthAnchor.month();
          return (
            <Button
              key={`${iso}-${monthAnchor.format("YYYY-MM")}`}
              size={btnSize}
              variant={isSel ? "filled" : "light"}
              color={isSel ? "blue" : "gray"}
              onClick={() => {
                onChange(iso);
                onMonthAnchorChange(d.startOf("month"));
              }}
              style={{
                minWidth: 0,
                paddingLeft: isCompact ? 4 : undefined,
                paddingRight: isCompact ? 4 : undefined,
                height: isCompact ? 28 : undefined,
                fontSize: isCompact ? 11 : undefined,
                background: "var(--bg-card)",
                opacity: isThisMonth ? 1 : 0.35,
                boxShadow: isSel ? "var(--shadow-soft-md)" : "var(--shadow-soft-sm)",
                transform: isSel ? "translateY(-1px)" : undefined,
                transition: "transform 0.12s ease, box-shadow 0.2s ease",
                borderRadius: "var(--radius-md)",
              }}
            >
              {d.date()}
            </Button>
          );
        })}
      </SimpleGrid>
    </>
  );

  if (!withShell) {
    return (
      <Box className={className} style={style}>
        {inner}
      </Box>
    );
  }

  return (
    <Box
      className={className}
      style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--input-border)",
        padding: pad,
        boxShadow: "var(--shadow-soft-md)",
        transition: "transform 0.15s ease",
        maxWidth: isCompact ? 268 : 320,
        ...style,
      }}
    >
      {inner}
    </Box>
  );
}
