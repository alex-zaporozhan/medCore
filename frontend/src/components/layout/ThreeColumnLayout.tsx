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
  /** Omni: узкая правая колонка под иконки (как свёрнутое левое меню). */
  omniRightCollapsed?: boolean;
  fullHeight?: boolean;
  /**
   * Если false — центр не оборачивается в ScrollArea (колонка сама задаёт внутренний скролл,
   * например фиксированная шапка/подвал чата и прокрутка только ленты сообщений).
   */
  centerColumnScrollable?: boolean;
}

function ColumnCell({ children, scrollable = true }: { children: ReactNode; scrollable?: boolean }) {
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
      {scrollable ? (
        <ScrollArea type="scroll" scrollbarSize={6} style={{ flex: 1, minHeight: 0 }}>
          {children}
        </ScrollArea>
      ) : (
        <Box style={{ flex: 1, minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column" }}>
          {children}
        </Box>
      )}
    </Box>
  );
}

function gridTemplateColumns(preset: ColumnWidthPreset, omniRightCollapsed?: boolean): string {
  switch (preset) {
    case "narrow-left":
      return "260px minmax(0, 1.4fr) minmax(0, 1fr)";
    case "equal":
      return "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)";
    case "omni-inspector": {
      const leftAndCenter = "minmax(188px, min(22vw, 252px)) minmax(0, 1fr)";
      if (omniRightCollapsed) {
        return `${leftAndCenter} 56px`;
      }
      /** Узкий список диалогов (~−25% к прошлому cap), без «пустых» 300px+ полос. */
      return `${leftAndCenter} minmax(272px, min(340px, 30vw))`;
    }
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
  omniRightCollapsed = false,
  fullHeight = true,
  centerColumnScrollable = true,
}: ThreeColumnLayoutProps) {
  const heightsStyle = fullHeight ? { minHeight: 0, height: "100%" as const } : { minHeight: 360 };

  return (
    <Box
      style={{
        display: "grid",
        gridTemplateColumns: gridTemplateColumns(preset, omniRightCollapsed),
        gap: "var(--mantine-spacing-md)",
        alignItems: "stretch",
        ...heightsStyle,
      }}
    >
      <ColumnCell>{left}</ColumnCell>
      <ColumnCell scrollable={centerColumnScrollable}>{center}</ColumnCell>
      <ColumnCell>{right}</ColumnCell>
    </Box>
  );
}
