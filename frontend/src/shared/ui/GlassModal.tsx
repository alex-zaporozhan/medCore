import { Modal, type ModalProps } from "@mantine/core";

/**
 * Modal with glass effect (backdrop blur). Global styles in index.css
 * also apply; this component sets Mantine overlay/content defaults.
 */
export function GlassModal({ children, ...props }: ModalProps) {
  return (
    <Modal
      centered
      overlayProps={{
        backgroundOpacity: 0.08,
        blur: 10,
      }}
      styles={{
        content: {
          background: "rgba(255, 255, 255, 0.92)",
          backdropFilter: "blur(10px)",
          boxShadow: "0 8px 32px rgba(62, 73, 84, 0.12)",
        },
      }}
      {...props}
    >
      {children}
    </Modal>
  );
}
