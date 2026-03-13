/**
 * Mantine theme: Smart Medical Gray-Blue palette (aligned with index.css).
 * Used in main.tsx via MantineProvider.
 */

import { createTheme } from "@mantine/core";

export const appTheme = createTheme({
  fontFamily: "Inter, system-ui, -apple-system, sans-serif",
  primaryColor: "brand",
  colors: {
    brand: [
      "#f8fafb",
      "#ebf1f4",
      "#dde8ed",
      "#c9dae3",
      "#b5ccd9",
      "#9cb4c4",
      "#8aa3b5",
      "#7a92a3",
      "#6a8192",
      "#5a7081",
    ],
  },
  defaultRadius: "md",
  components: {
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
            boxShadow: "0 8px 32px rgba(62, 73, 84, 0.12)",
          },
        },
      },
    },
  },
});
