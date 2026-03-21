import { Box, ScrollArea } from "@mantine/core";
import type { ReactNode } from "react";

/**
 * Пресеты колонок — только валидные значения для `grid-template-columns`
 * (раньше третья колонка использовала `fr` как `width` во Flex — браузер игнорировал,
 * из‑за чего правая панель сжималась по содержимому и «прыгала» при смене вкладок).
 */
export type ColumnWidthPreset =
  | "narrow-left"
  | "equal"
  | "wide-center"
  /** Фиксированная ширина инспектора справа (Omni Chat и др.) — стабильная вёрстка. */
  | "omni-inspector";

interface ThreeColumnLayoutProps {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  preset?: ColumnWidthPreset;
  fullHeight?: boolean;
}

function ColumnCell({ children }: { children: ReactNode }) {
  return (
    <Box
      style={{
        minWidth: 0,
        minHeight: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <ScrollArea type="scroll" scrollbarSize={6} style={{ flex: 1, minHeight: 0 }}>
        {children}
      </ScrollArea>
    </Box>
  );
}

function gridTemplateColumns(preset: ColumnWidthPreset): string {
  switch (preset) {
    case "narrow-left":
      return "260px minmax(0, 1.4fr) minmax(0, 1fr)";
    case "equal":
      return "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)";
    case "omni-inspector":
      return "260px minmax(0, 1fr) 360px";
    case "wide-center":
    default:
      return "280px minmax(0, 1fr) 360px";
  }
}

export function ThreeColumnLayout({
  left,
  center,
  right,
  preset = "wide-center",
  fullHeight = true,
}: ThreeColumnLayoutProps) {
  const heightsStyle = fullHeight ? { minHeight: 0, height: "100%" as const } : { minHeight: 360 };

  return (
    <Box
      style={{
        display: "grid",
        gridTemplateColumns: gridTemplateColumns(preset),
        gap: "var(--mantine-spacing-md)",
        alignItems: "stretch",
        ...heightsStyle,
      }}
    >
      <ColumnCell>{left}</ColumnCell>
      <ColumnCell>{center}</ColumnCell>
      <ColumnCell>{right}</ColumnCell>
    </Box>
  );
}
