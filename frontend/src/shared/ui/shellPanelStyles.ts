import type { DrawerProps, MantineTheme, ModalProps } from "@mantine/core";
import type { CSSProperties } from "react";

/**
 * AppShell sets this on `:root` while the navbar is in flow.
 * Below the navbar breakpoint it becomes `0px` (navbar off-canvas).
 */
export const ADMIN_SHELL_NAVBAR_OFFSET = "var(--app-shell-navbar-offset, 0px)";

/** Shared overlay for glass modal and admin detail drawers (`AdminDrawer`). */
export const SHELL_OVERLAY_PROPS: NonNullable<ModalProps["overlayProps"]> = {
  backgroundOpacity: 0.08,
  blur: 10,
  /** Do not dim/block the admin navbar — Modal portals to `document.body`. */
  style: { left: ADMIN_SHELL_NAVBAR_OFFSET },
};

/**
 * Mantine Modal + `lockScroll` uses remove-scroll (`pointer-events: none` on `body`).
 * A wide dialog that covers the sidebar would then trap the user on the page.
 * Keep the shell navbar clickable (overlay/inner inset to the content column).
 */
export const ADMIN_NAV_SAFE_MODAL_PROPS: Pick<ModalProps, "lockScroll" | "trapFocus"> = {
  lockScroll: false,
  /** Tab stays in the dialog; mouse can still hit the navbar (lockScroll off + overlay inset). */
  trapFocus: true,
};

/**
 * Position the dialog in the main column (right of the navbar), then let Mantine
 * `justify-content: center` work. `paddingLeft: navbar` on a full-viewport inner
 * left-aligns wide dialogs and leaves a dead gap on the right.
 */
export const SHELL_MODAL_NAV_INNER_STYLE: CSSProperties = {
  left: ADMIN_SHELL_NAVBAR_OFFSET,
  right: 0,
  width: "auto",
  display: "flex",
  justifyContent: "center",
  boxSizing: "border-box",
  pointerEvents: "none",
};

/** Center modal content — aligned with legacy `GlassModal` look. */
export const SHELL_MODAL_CONTENT_STYLE: CSSProperties = {
  background: "var(--overlay-glass-surface)",
  backdropFilter: "blur(10px)",
  boxShadow: "var(--shadow-soft-md)",
  borderRadius: "var(--mantine-radius-lg)",
  border: "1px solid var(--mantine-color-gray-2)",
  overflow: "hidden",
};

const shellDrawerBase = {
  content: {
    background: "var(--drawer-glass-surface)",
    backdropFilter: "blur(10px)",
    boxShadow: "var(--shadow-soft-md)",
    borderTopLeftRadius: "var(--mantine-radius-md)",
    borderBottomLeftRadius: "var(--mantine-radius-md)",
    border: "1px solid var(--mantine-color-gray-2)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    maxHeight: "100dvh",
  },
  header: {
    paddingBottom: "var(--mantine-spacing-sm)",
    marginBottom: 0,
    flexShrink: 0,
    // Без light-dark() — шире поддержка движков; Mantine подставляет палитру через переменные темы
    borderBottom: "1px solid var(--mantine-color-gray-3)",
  },
  /** Как у `shellModalBase.body`: длинные формы не обрезают кнопки внизу. */
  body: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto",
    overscrollBehavior: "contain",
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
  overlay: {
    left: ADMIN_SHELL_NAVBAR_OFFSET,
  },
  inner: {
    ...SHELL_MODAL_NAV_INNER_STYLE,
  },
  content: {
    ...SHELL_MODAL_CONTENT_STYLE,
    pointerEvents: "auto",
    // Ensure footer-like sections can be fixed inside body.
    display: "flex",
    flexDirection: "column",
    // Guardrail: never allow modal to exceed viewport.
    maxHeight: "min(92vh, 900px)",
  },
  // Mantine modal body must be scrollable; otherwise long forms hide actions.
  body: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto",
    overscrollBehavior: "contain",
  },
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
