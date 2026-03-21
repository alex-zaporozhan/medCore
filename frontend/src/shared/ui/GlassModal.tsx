import { Modal, type ModalProps } from "@mantine/core";
import { useMemo } from "react";
import { mergeModalStyles, SHELL_OVERLAY_PROPS } from "./shellPanelStyles";

/**
 * Modal with glass effect (backdrop blur). Shares overlay/content tokens with `AdminDrawer` via `shellPanelStyles`.
 */
export function GlassModal({ children, overlayProps, styles, ...props }: ModalProps) {
  const mergedStyles = useMemo(() => mergeModalStyles(styles), [styles]);
  const mergedOverlay = useMemo(
    () => ({ ...SHELL_OVERLAY_PROPS, ...overlayProps }),
    [overlayProps]
  );
  return (
    <Modal centered overlayProps={mergedOverlay} styles={mergedStyles} {...props}>
      {children}
    </Modal>
  );
}
