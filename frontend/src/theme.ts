/**
 * Crisp SaaS (светлая админка): приглушённые палитры (Slate / Indigo / Rose / Emerald),
 * многослойные тени, карточки с микрограницей.
 * Канон: `docs/ARCH_FRONTEND_UI_LOGIC.md` · `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` §7–§9
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

/** Layered shadows — `docs/ARCH_FRONTEND_UI_LOGIC.md` §2.2 */
const crispShadows = {
  xs: "0 1px 2px rgba(0, 0, 0, 0.04)",
  sm: "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)",
  md: "0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)",
  lg: "0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.025)",
  xl: "0 20px 25px -5px rgba(0,0,0,0.05), 0 10px 10px -5px rgba(0,0,0,0.02)",
};

/** Slate Indigo — primary; без «ядовитого» дефолтного indigo Mantine */
const slateIndigo: MantineColorsTuple = [
  "#EEF2F6",
  "#E0E7FF",
  "#C7D2FE",
  "#A5B4FC",
  "#818CF8",
  "#6366F1",
  "#4F46E5",
  "#4338CA",
  "#3730A3",
  "#312E81",
];

/** Холодный Slate вместо нейтрального gray */
const slateCool: MantineColorsTuple = [
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

/** Rose — приглушённый «красный» */
const roseMuted: MantineColorsTuple = [
  "#fff1f2",
  "#ffe4e6",
  "#fecdd3",
  "#fda4af",
  "#fb7185",
  "#f43f5e",
  "#e11d48",
  "#be123c",
  "#9f1239",
  "#881337",
];

/** Emerald — спокойный «зелёный» / успех */
const emeraldCalm: MantineColorsTuple = [
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

/** Blue — мягкий slate-blue (не кислотный) */
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

/** Совместимость: ключ `dark` — та же холодная шкала (расписание, вторичные акценты) */
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
  },
  spacing: {
    xs: rem(8),
    sm: rem(12),
    md: rem(16),
    lg: rem(24),
    xl: rem(32),
  },
  primaryColor: "indigo",
  primaryShade: 6,
  defaultRadius: "sm",
  colors: {
    indigo: slateIndigo,
    gray: slateCool,
    red: roseMuted,
    green: emeraldCalm,
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
          transition: "background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease",
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
            background: "rgba(255, 255, 255, 0.92)",
            backdropFilter: "blur(10px)",
            boxShadow: "0 12px 40px rgba(15, 23, 42, 0.14)",
          },
        },
      },
    },
  },
});
