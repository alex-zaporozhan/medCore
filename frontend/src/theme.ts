/**
 * Swiss Slate / Ink (светлая админка): brand = сине-графит, холодные нейтрали,
 * многослойные тени с подтоном ink, карточки с микрограницей.
 * Канон темы: этот файл, `index.css` и Mantine theme override.
 */

import {
  Badge,
  Button,
  Card,
  Paper,
  createTheme,
  rem,
  type MantineColorsTuple,
} from "@mantine/core";

/** Тени Crisp × Ink — шкала в этом файле. */
const crispShadows = {
  xs: "0 1px 2px rgba(15, 20, 25, 0.05)",
  sm: "0 1px 2px rgba(15,20,25,0.05), 0 4px 12px rgba(15,20,25,0.06)",
  md: "0 4px 8px rgba(15,20,25,0.06), 0 16px 40px rgba(15,20,25,0.08)",
  lg: "0 10px 15px -3px rgba(15,20,25,0.07), 0 4px 6px -2px rgba(15,20,25,0.05)",
  xl: "0 20px 25px -5px rgba(15,20,25,0.08), 0 10px 10px -5px rgba(15,20,25,0.04)",
};

/** Swiss Slate / Ink — brand (шкала ink-50…900). */
const swissInk: MantineColorsTuple = [
  "#e8eef3", // ink-50
  "#dce4eb", // между 50 и 100
  "#c5d4e0", // ink-100
  "#8a9faf", // ink-300
  "#6b7f90", // между 300 и 500
  "#4a5f73", // ink-500
  "#1c2e45", // primary
  "#152338", // hover
  "#0f1a28", // между hover и 900
  "#0a1018", // ink-900
];

/** Нейтраль Swiss (поверхности + лестница n-50…text main). */
const slateCool: MantineColorsTuple = [
  "#f4f6f8", // bg app
  "#eef1f4", // bg hover
  "#e2e6ea", // border
  "#d0d7de", // border 2°
  "#9aa8b3", // n-400
  "#5c6d7a", // text ·
  "#3d4f5c", // n-700
  "#2a3844",
  "#1a2430",
  "#0f1419", // text main
];

/** Danger / error — якоря из свотчей §1: danger bg, danger, danger text */
const swissDanger: MantineColorsTuple = [
  "#fef2f2",
  "#fee2e2",
  "#fecaca",
  "#fca5a5",
  "#f87171",
  "#ef4444",
  "#dc2626",
  "#b42318",
  "#9f1239",
  "#7f1d1d",
];

/** Success — якоря §1: success bg #ecfdf5, success #065f46 */
const swissSuccess: MantineColorsTuple = [
  "#ecfdf5",
  "#d1fae5",
  "#a7f3d0",
  "#6ee7b7",
  "#34d399",
  "#10b981",
  "#059669",
  "#047857",
  "#065f46",
  "#064e3b",
];

/** Warning — якоря §1: warn bg #fffbeb, warn #b45309 */
const swissWarning: MantineColorsTuple = [
  "#fffbeb",
  "#fef3c7",
  "#fde68a",
  "#fcd34d",
  "#fbbf24",
  "#f59e0b",
  "#d97706",
  "#b45309",
  "#92400e",
  "#78350f",
];

/** Blue — info / ссылки второго порядка (не смешивать с brand-ink на CTA) */
const blueSoft: MantineColorsTuple = [
  "#f8fafc",
  "#eff6ff",
  "#dbeafe",
  "#bfdbfe",
  "#93c5fd",
  "#60a5fa",
  "#3b82f6",
  "#2563eb",
  "#1d4ed8",
  "#1e3a8a",
];

/** Совместимость: ключ `dark` — та же холодная шкала */
const slateDark: MantineColorsTuple = [...slateCool];

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
    lg: rem(18),
    xl: rem(20),
  },
  spacing: {
    xs: rem(4),
    sm: rem(8),
    md: rem(12),
    lg: rem(16),
    xl: rem(24),
    "2xl": rem(32),
  },
  primaryColor: "brand",
  primaryShade: 6,
  defaultRadius: "sm",
  colors: {
    brand: swissInk,
    /** Алиас для существующих `color="indigo"` — та же шкала ink */
    indigo: swissInk,
    gray: slateCool,
    red: swissDanger,
    green: swissSuccess,
    yellow: swissWarning,
    blue: blueSoft,
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
    Badge: Badge.extend({
      defaultProps: {
        variant: "light",
      },
      styles: (theme, props) => {
        if (props.variant === "filled") {
          const colorKey = (props.color ?? "gray") as keyof typeof theme.colors;
          const scale = theme.colors[colorKey];
          if (scale && Array.isArray(scale)) {
            return {
              root: {
                backgroundColor: scale[0],
                color: scale[7],
                border: `1px solid ${scale[2]}`,
              },
            };
          }
        }
        return {};
      },
    }),
    Paper: Paper.extend({
      defaultProps: {
        withBorder: true,
        shadow: "sm",
        radius: "sm",
        bg: "#ffffff",
      },
      styles: {
        root: {
          borderColor: "var(--mantine-color-gray-2)",
          backgroundColor: "#ffffff",
        },
      },
    }),
    Card: Card.extend({
      defaultProps: {
        withBorder: true,
        shadow: "sm",
        radius: "sm",
        bg: "#ffffff",
      },
      styles: {
        root: {
          borderColor: "var(--mantine-color-gray-2)",
          backgroundColor: "#ffffff",
        },
      },
    }),
    Button: Button.extend({
      defaultProps: {
        radius: "sm",
        fw: 500,
      },
      styles: (theme, props) => {
        const root: Record<string, string | number | undefined> = {
          transition: "background-color 180ms ease, border-color 180ms ease, box-shadow 180ms ease",
        };
        if (props.variant === "default") {
          Object.assign(root, {
            backgroundColor: "#ffffff",
            border: `1px solid ${theme.colors.gray[3]}`,
            color: theme.colors.gray[7],
            boxShadow: theme.shadows.xs,
            "&:hover": {
              backgroundColor: theme.colors.gray[0],
            },
          });
        }
        if (props.variant === "filled") {
          Object.assign(root, {
            boxShadow: theme.shadows.sm,
          });
        }
        return { root };
      },
    }),
    Table: {
      defaultProps: {
        verticalSpacing: "sm",
        horizontalSpacing: "md",
        withRowBorders: true,
        highlightOnHover: true,
      },
      styles: {
        thead: {
          backgroundColor: "var(--mantine-color-gray-0)",
        },
      },
    },
    Modal: {
      defaultProps: {
        centered: true,
        transition: "fade",
        overlayProps: {
          backgroundOpacity: 0.08,
          blur: 10,
        },
        styles: {
          content: {
            background: "var(--overlay-glass-surface)",
            backdropFilter: "blur(10px)",
            boxShadow: "var(--shadow-soft-md)",
          },
        },
      },
    },
  },
});
