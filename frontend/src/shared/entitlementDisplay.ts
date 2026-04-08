/**
 * Человекочитаемые подписи для entitlement-ключей (МП §4, Phase0 alignment).
 * Используются в админке: карточка «Подписка и возможности».
 */

export type EntitlementDisplay = {
  title: string;
  hint: string;
};

/** Ключи, которые участвуют в коммерческом «разрезе» (кроме базы). */
export const COMMERCIAL_ENTITLEMENT_KEYS: readonly string[] = [
  "crm.pipeline",
  "retention.bundle",
  "tasks.kanban",
  "marketing.attribution",
  "omni.embed.bundle",
  "ai.assistant.chat",
  "ai.rag.org_kb",
  "commerce.store_network",
  "erp.reporting_plus",
  "import.crm_v1",
  "omni.extended",
  "network.multi_clinic",
] as const;

export const ENTITLEMENT_LABELS: Record<string, EntitlementDisplay> = {
  "core.base": {
    title: "База продукта",
    hint: "Запись, пациенты, расписание, предоплата, уведомления, базовые отчёты",
  },
  "crm.pipeline": {
    title: "CRM и воронка",
    hint: "Сделки, продажи, воронка в интерпретации продукта",
  },
  "retention.bundle": {
    title: "Retention",
    hint: "Удержание и сценарии возврата пациентов",
  },
  "tasks.kanban": {
    title: "Задачи и Kanban",
    hint: "Доски задач для команды клиники",
  },
  "marketing.attribution": {
    title: "Маркетинг и атрибуция",
    hint: "Кампании, recall, маркетинговая аналитика",
  },
  "omni.embed.bundle": {
    title: "Встраивание (embed)",
    hint: "Виджет записи, API-ключи, сценарии встраивания на сайт",
  },
  "ai.assistant.chat": {
    title: "AI-ассистент (чат)",
    hint: "Омниканальный AI для ответов клиентам",
  },
  "ai.rag.org_kb": {
    title: "RAG база знаний",
    hint: "Документы организации для ответов AI",
  },
  "commerce.store_network": {
    title: "Commerce / магазин",
    hint: "Сетевой склад и торговые сценарии",
  },
  "erp.reporting_plus": {
    title: "Расширенная аналитика ERP",
    hint: "Дополнительные отчёты и срезы",
  },
  "import.crm_v1": {
    title: "Импорт CRM",
    hint: "Импорт из внешней CRM (по продукту)",
  },
  "omni.extended": {
    title: "Расширенный omnichannel",
    hint: "Дополнительные каналы и сценарии",
  },
  "network.multi_clinic": {
    title: "Несколько локаций",
    hint: "Единая организация, несколько клиник",
  },
};

export function labelForEntitlementKey(key: string): EntitlementDisplay {
  return (
    ENTITLEMENT_LABELS[key] ?? {
      title: key,
      hint: "Опция платформы",
    }
  );
}
