/**
 * Семантические цвета Mantine (`color` на Button, ThemeIcon, Badge и т.д.).
 * Политика: цвет = смысл (метрика, дата, AI, риск), не «заливка экрана».
 */

export const SEMANTIC = {
  metrics: {
    appointments: "indigo",
    revenue: "teal",
    patients: "blue",
    cancellations: "red",
  },
  /** Кнопки навигации по дате в расписании (вчера / сегодня / завтра) */
  dateNav: {
    yesterday: "gray",
    today: "indigo",
    tomorrow: "teal",
  },
  /** AI / RAG — палитра `ai` в теме (не путать с графитовым primary) */
  ai: {
    accent: "ai",
  },
  status: {
    success: "teal",
    warning: "orange",
    danger: "red",
    neutral: "gray",
  },
  /**
   * Кнопки: один смысл — один оттенок; без «радужного» chrome.
   * `send` — сообщения и коммуникация; `confirm` — подтверждение, формы, оплата; `danger` — удаление;
   * `dismiss` — отмена/закрыть; `link` — вторичные ссылки PAW.
   */
  action: {
    send: "blue",
    confirm: "teal",
    danger: "red",
    dismiss: "gray",
    link: "blue",
  },
} as const;

export type SemanticMetricKey = keyof typeof SEMANTIC.metrics;
export type SemanticDateNavKey = keyof typeof SEMANTIC.dateNav;
export type SemanticActionKey = keyof typeof SEMANTIC.action;
