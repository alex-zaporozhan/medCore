import type { DrawerProps, MantineTheme, ModalProps } from "@mantine/core";
import type { CSSProperties } from "react";

/** Shared overlay for glass modal and admin detail drawers (TECH_PASSPORT / ARCH_FRONTEND_ADMIN_SHELL). */
export const SHELL_OVERLAY_PROPS: NonNullable<ModalProps["overlayProps"]> = {
  backgroundOpacity: 0.08,
  blur: 10,
};

/** Center modal content — aligned with legacy `GlassModal` look. */
export const SHELL_MODAL_CONTENT_STYLE: CSSProperties = {
  background: "rgba(255, 255, 255, 0.92)",
  backdropFilter: "blur(10px)",
  boxShadow: "0 8px 32px rgba(62, 73, 84, 0.12)",
  borderRadius: "var(--mantine-radius-lg)",
  border: "1px solid var(--mantine-color-gray-2)",
  overflow: "hidden",
};

const shellDrawerBase = {
  content: {
    background: "rgba(255, 255, 255, 0.96)",
    backdropFilter: "blur(10px)",
    boxShadow: "0 8px 32px rgba(62, 73, 84, 0.14)",
    borderTopLeftRadius: "var(--mantine-radius-md)",
    borderBottomLeftRadius: "var(--mantine-radius-md)",
    border: "1px solid var(--mantine-color-gray-2)",
    overflow: "hidden",
  },
  header: {
    paddingBottom: "var(--mantine-spacing-sm)",
    marginBottom: 0,
    // Без light-dark() — шире поддержка движков; Mantine подставляет палитру через переменные темы
    borderBottom: "1px solid var(--mantine-color-gray-3)",
  },
};

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

type DrawerStylesFn = (
  theme: MantineTheme,
  props: DrawerProps,
  ctx: unknown
) => Record<string, unknown> | undefined;

type ModalStylesFn = (
  theme: MantineTheme,
  props: ModalProps,
  ctx: unknown
) => Record<string, unknown> | undefined;

const shellModalBase = {
  content: { ...SHELL_MODAL_CONTENT_STYLE },
};

/** Merge glass modal content + overlay-related sections with user `styles` (object or Mantine callback). */
export function mergeModalStyles(user: ModalProps["styles"] | undefined): ModalProps["styles"] {
  if (!user) return shellModalBase as NonNullable<ModalProps["styles"]>;
  if (typeof user === "function") {
    const styleFn = user as ModalStylesFn;
    return ((theme: MantineTheme, props: ModalProps, ctx: unknown) => {
      const resolved = styleFn(theme, props, ctx);
      if (!resolved || !isPlainObject(resolved)) return { ...shellModalBase };
      return mergeStyleRecords(shellModalBase as Record<string, unknown>, resolved as Record<string, unknown>) as NonNullable<
        ModalProps["styles"]
      >;
    }) as NonNullable<ModalProps["styles"]>;
  }
  return mergeStyleRecords(shellModalBase as Record<string, unknown>, user as Record<string, unknown>) as NonNullable<
    ModalProps["styles"]
  >;
}

/** Deep-merge Mantine `styles` records (shallow per section; nested objects merged). */
export function mergeDrawerStyles(
  user: DrawerProps["styles"] | undefined
): DrawerProps["styles"] {
  if (!user) return shellDrawerBase as NonNullable<DrawerProps["styles"]>;
  if (typeof user === "function") {
    const styleFn = user as DrawerStylesFn;
    return ((theme: MantineTheme, props: DrawerProps, ctx: unknown) => {
      const resolved = styleFn(theme, props, ctx);
      if (!resolved || !isPlainObject(resolved)) return { ...shellDrawerBase };
      return mergeStyleRecords(shellDrawerBase as Record<string, unknown>, resolved) as NonNullable<
        DrawerProps["styles"]
      >;
    }) as NonNullable<DrawerProps["styles"]>;
  }
  return mergeStyleRecords(shellDrawerBase as Record<string, unknown>, user as Record<string, unknown>) as NonNullable<
    DrawerProps["styles"]
  >;
}

function mergeStyleRecords(
  a: Record<string, unknown>,
  b: Record<string, unknown>
): Record<string, unknown> {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  const out: Record<string, unknown> = {};
  for (const k of keys) {
    const av = a[k];
    const bv = b[k];
    if (isPlainObject(av) && isPlainObject(bv)) {
      out[k] = { ...av, ...bv };
    } else if (bv !== undefined) {
      out[k] = bv;
    } else {
      out[k] = av;
    }
  }
  return out;
}
