import { Modal, type ModalProps } from "@mantine/core";
import { useMemo } from "react";
import { mergeModalStyles, SHELL_OVERLAY_PROPS } from "./shellPanelStyles";

/**
 * Modal with glass effect (backdrop blur). Shares overlay/content tokens with `AdminDrawer` via `shellPanelStyles`.
 */
export function GlassModal({
  children,
  overlayProps,
  styles,
  lockScroll = false,
  trapFocus = true,
  ...props
}: ModalProps) {
  const mergedStyles = useMemo(() => mergeModalStyles(styles), [styles]);
  const mergedOverlay = useMemo(
    () => ({
      ...SHELL_OVERLAY_PROPS,
      ...overlayProps,
      style: { ...SHELL_OVERLAY_PROPS.style, ...overlayProps?.style },
    }),
    [overlayProps]
  );
  return (
    <Modal
      centered
      {...props}
      lockScroll={lockScroll}
      trapFocus={trapFocus}
      overlayProps={mergedOverlay}
      styles={mergedStyles}
    >
      {children}
    </Modal>
  );
}
