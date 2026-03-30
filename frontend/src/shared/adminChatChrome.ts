import type { CSSProperties } from "react";

/**
 * DGN-P1-03 — единые визуальные токены для админ-чатов (patient / staff / далее omni),
 * чтобы пузыри и панели не расходились по смыслу «свой / чужой».
 */
export function adminChatIncomingBubbleStyle(extra?: CSSProperties): CSSProperties {
  return {
    borderRadius: "var(--radius-md)",
    backgroundColor: "var(--bg-main)",
    ...extra,
  };
}

export function adminChatOutgoingBubbleStyle(extra?: CSSProperties): CSSProperties {
  return {
    borderRadius: "var(--radius-md)",
    backgroundColor: "var(--primary-alpha-12)",
    ...extra,
  };
}

/** Регион списка сообщений — landmark для скринридеров (DGN-P0-05 минимум). */
export const ADMIN_CHAT_MESSAGES_REGION = {
  component: "section" as const,
  "aria-label": "Сообщения переписки",
};

/**
 * Omni-чат: входящие от клиента (карточка на нити). Исходящие — насыщенный indigo для контраста с PWA-пузырями.
 * DGN-P1-03 — единая точка смены токенов для всех админ-чатов.
 */
export function adminChatOmniClientInboundBubbleStyle(extra?: CSSProperties): CSSProperties {
  return {
    borderRadius: "var(--mantine-radius-md)",
    boxShadow: "var(--mantine-shadow-xs)",
    backgroundColor: "var(--bg-card)",
    border: "1px solid var(--mantine-color-gray-2)",
    ...extra,
  };
}

export function adminChatOmniOutboundBubbleStyle(extra?: CSSProperties): CSSProperties {
  return {
    borderRadius: "var(--mantine-radius-md)",
    boxShadow: "var(--mantine-shadow-xs)",
    backgroundColor: "var(--mantine-color-indigo-6)",
    ...extra,
  };
}

export function adminChatOmniHiddenBubbleStyle(extra?: CSSProperties): CSSProperties {
  return {
    borderRadius: "var(--mantine-radius-md)",
    boxShadow: "var(--mantine-shadow-xs)",
    backgroundColor: "var(--muted-alpha-20)",
    border: "1px solid var(--mantine-color-gray-3)",
    opacity: 0.9,
    ...extra,
  };
}
