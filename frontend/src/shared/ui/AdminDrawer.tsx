import { Drawer, type DrawerProps } from "@mantine/core";
import { useMemo } from "react";
import { mergeDrawerStyles, SHELL_OVERLAY_PROPS } from "./shellPanelStyles";

/**
 * Right detail panel with shared shell (overlay blur, glass-ish content, header rule).
 * Use instead of raw Mantine `Drawer` for entity/forms from tables — see `TECH_PASSPORT_FRONTEND_UI_LOGIC.md`, `ARCH_FRONTEND_ADMIN_SHELL_DRAWER_2026`.
 */
export function AdminDrawer({
  overlayProps,
  styles,
  position = "right",
  closeButtonProps,
  ...rest
}: DrawerProps) {
  const mergedStyles = useMemo(() => mergeDrawerStyles(styles), [styles]);
  const mergedOverlay = useMemo(
    () => ({ ...SHELL_OVERLAY_PROPS, ...overlayProps }),
    [overlayProps]
  );
  const mergedClose = useMemo(
    () => ({ "aria-label": "Закрыть панель", ...closeButtonProps }),
    [closeButtonProps]
  );
  return (
    <Drawer
      position={position}
      overlayProps={mergedOverlay}
      styles={mergedStyles}
      closeButtonProps={mergedClose}
      {...rest}
    />
  );
}
