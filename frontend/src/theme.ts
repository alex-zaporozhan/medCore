/**
 * Design System «Инструмент» (Midnight & Graphite): Slate surfaces, графитовый primary,
 * палитра `ai` для RAG/AI; тени минимальны — границы важнее объёма.
 * Канон: `docs/artifacts/ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md`
 */

import { createTheme, rem, type MantineColorsTuple } from "@mantine/core";

/** Crisp shadows — в основном для модалок; карточки по умолчанию без тени */
const crispShadows = {
  xs: "0 1px 2px rgba(0, 0, 0, 0.05)",
  sm: "0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)",
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
};

/** Slate scale — primary `dark` ≈ графит Action #1E293B @ shade 8 */
const slateDark: MantineColorsTuple = [
  "#f8fafc",
  "#f1f5f9",
  "#e2e8f0",
  "#cbd5e1",
  "#94a3b8",
  "#64748b",
  "#475569",
  "#334155",
  "#1e293b",
  "#0f172a",
];

const aiViolet: MantineColorsTuple = [
  "#f5f3ff",
  "#ede9fe",
  "#ddd6fe",
  "#c4b5fd",
  "#a78bfa",
  "#8b5cf6",
  "#7c3aed",
  "#6d28d9",
  "#5b21b6",
  "#4c1d95",
];

export const appTheme = createTheme({
  fontFamily: "Inter, system-ui, -apple-system, sans-serif",
  fontSizes: {
    xs: rem(12),
    sm: rem(14),
    md: rem(16),
  },
  spacing: {
    xs: rem(8),
    sm: rem(12),
    md: rem(16),
    lg: rem(24),
    xl: rem(32),
  },
  primaryColor: "dark",
  primaryShade: 8,
  defaultRadius: "sm",
  colors: {
    dark: slateDark,
    ai: aiViolet,
  },
  headings: {
    fontFamily: "Inter, system-ui, -apple-system, sans-serif",
    fontWeight: "700",
    sizes: {
      h1: { fontSize: rem(28), lineHeight: "1.3", fontWeight: "700" },
      h2: { fontSize: rem(24), lineHeight: "1.35", fontWeight: "700" },
      h3: { fontSize: rem(20), lineHeight: "1.4", fontWeight: "700" },
      h4: { fontSize: rem(18), lineHeight: "1.45", fontWeight: "700" },
    },
  },
  shadows: crispShadows,
  components: {
    Text: {
      defaultProps: {
        size: "sm",
      },
    },
    Paper: {
      defaultProps: {
        withBorder: true,
        shadow: "none",
        radius: "sm",
        bg: "white",
      },
    },
    Card: {
      defaultProps: {
        withBorder: true,
        shadow: "none",
        radius: "sm",
        bg: "white",
      },
    },
    Button: {
      defaultProps: {
        radius: "sm",
        fw: 600,
      },
      styles: {
        root: {
          transition: "background-color 0.2s ease",
        },
      },
    },
    Table: {
      defaultProps: {
        verticalSpacing: "sm",
        horizontalSpacing: "md",
        withRowBorders: true,
        highlightOnHover: true,
      },
      styles: {
        thead: {
          backgroundColor: "#f8fafc",
        },
      },
    },
    Modal: {
      defaultProps: {
        overlayProps: {
          backgroundOpacity: 0.08,
          blur: 10,
        },
        styles: {
          content: {
            background: "rgba(255, 255, 255, 0.92)",
            backdropFilter: "blur(10px)",
            boxShadow: "0 12px 40px rgba(15, 23, 42, 0.14)",
          },
        },
      },
    },
  },
});
