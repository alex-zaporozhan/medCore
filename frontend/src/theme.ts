/**
 * Mantine theme: единый акцент **indigo** (согласован с активным пунктом тёмного сайдбара админки).
 * Шрифт: Inter (подключается в `main.tsx` через `@fontsource/inter`).
 */

import { createTheme } from "@mantine/core";

export const appTheme = createTheme({
  fontFamily: "Inter, system-ui, -apple-system, sans-serif",
  headings: {
    fontFamily: "Inter, system-ui, -apple-system, sans-serif",
    fontWeight: "600",
  },
  primaryColor: "indigo",
  /** Чуть мягче дефолтного акцента (shade 6), без «вырви глаз» на больших CTA */
  primaryShade: { light: 5, dark: 6 },
  defaultRadius: "md",
  components: {
    Paper: {
      defaultProps: {
        shadow: "sm",
      },
    },
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
            boxShadow: "0 12px 40px rgba(15, 23, 42, 0.14)",
          },
        },
      },
    },
  },
});
