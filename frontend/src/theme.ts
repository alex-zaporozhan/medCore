/**
 * Enterprise B2B: корпоративный цвет Swiss Slate (глубокий серо-сине-зелёный).
 * primaryColor `slate`, primaryShade 7 (#2a3843) для основных кнопок; hover → индекс 8 (#1e293b).
 * Канон: этот файл и `index.css`.
 */

import {
  Badge,
  Button,
  Card,
  Paper,
  PasswordInput,
  TextInput,
  Title,
  createTheme,
  rem,
  type MantineColorsTuple,
} from "@mantine/core";

/** Тени в холодном нейтрале (slate / ink). */
const crispShadows = {
  xs: "0 1px 2px rgba(15, 23, 42, 0.04)",
  sm: "0 1px 3px rgba(15, 23, 42, 0.06), 0 6px 16px rgba(30, 41, 59, 0.06)",
  md: "0 4px 12px rgba(15, 23, 42, 0.07), 0 2px 6px rgba(15, 23, 42, 0.04)",
  lg: "0 12px 32px -8px rgba(15, 23, 42, 0.1), 0 8px 20px -6px rgba(30, 41, 59, 0.07)",
  xl: "0 24px 56px -12px rgba(15, 23, 42, 0.14), 0 12px 28px -8px rgba(30, 41, 59, 0.1), 0 0 0 1px rgba(148, 163, 184, 0.12)",
};

/** Swiss Slate — основной корпоративный; кнопки: [7], hover: [8]. */
const swissSlate: MantineColorsTuple = [
  "#f1f5f9",
  "#e2e8f0",
  "#cbd5e1",
  "#94a3b8",
  "#64748b",
  "#475569",
  "#334155",
  "#2a3843",
  "#1e293b",
  "#0f172a",
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
  primaryColor: "slate",
  primaryShade: 7,
  defaultRadius: "md",
  colors: {
    slate: swissSlate,
    /** Алиас для существующего `color="brand"` в админке и маркетинге */
    brand: swissSlate,
    indigo: swissSlate,
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
        radius: "lg",
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
        radius: "lg",
        bg: "#ffffff",
      },
      styles: {
        root: {
          borderColor: "var(--mantine-color-gray-2)",
          backgroundColor: "#ffffff",
        },
      },
    }),
    TextInput: TextInput.extend({
      defaultProps: {
        radius: "md",
      },
    }),
    PasswordInput: PasswordInput.extend({
      defaultProps: {
        radius: "md",
      },
    }),
    Title: Title.extend({
      styles: (_theme, props) => {
        const order = props.order ?? 1;
        if (order === 1 || order === 2) {
          return { root: { color: "#0f172a" } };
        }
        return {};
      },
    }),
    Button: Button.extend({
      defaultProps: {
        radius: "md",
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
          const colorKey = (props.color ?? theme.primaryColor) as string;
          if (colorKey === "slate" || colorKey === "brand" || colorKey === "indigo") {
            const s = theme.colors.slate;
            Object.assign(root, {
              backgroundColor: s[7],
              color: theme.white,
              boxShadow: theme.shadows.sm,
              "&:hover": { backgroundColor: s[8] },
              "&:active": { backgroundColor: s[9] },
            });
          } else {
            Object.assign(root, {
              boxShadow: theme.shadows.sm,
            });
          }
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
