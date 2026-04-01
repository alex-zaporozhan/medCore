import type { ActionIconProps, ButtonProps } from "@mantine/core";

/**
 * Единый визуальный контекст для стены персонала (Swiss Slate / Ink):
 * `brand` (ink), не нейтральный «серый util».
 */
export const STAFF_FEED_CHROME = {
  actionIcon: {
    variant: "light",
    color: "brand",
    size: "lg",
    radius: "md",
  } satisfies Partial<ActionIconProps>,

  /** Вторичные текстовые кнопки (ответ, выбор файла) */
  subtleButton: {
    variant: "subtle",
    color: "brand",
  } satisfies Partial<ButtonProps>,

  /** Основные CTA блока ленты */
  primaryButton: {
    variant: "filled",
    color: "brand",
  } satisfies Partial<ButtonProps>,
} as const;
