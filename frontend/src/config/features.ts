/**
 * Флаги «модуля UI» для админки/пациентского приложения.
 * В SaaS с `entitlement_enforced` значения выводятся из сессии (`resolveProductFeatures`),
 * иначе — полный доступ как в коробке/legacy (все true).
 */

export type ProductFeatures = {
  channels_ui: boolean;
  integrations_1c: boolean;
  styling: boolean;
  stickers: boolean;
  discounts: boolean;
  feed_stories: boolean;
  notification_policy_advanced: boolean;
};

const ALL_ENABLED: ProductFeatures = {
  channels_ui: true,
  integrations_1c: true,
  styling: true,
  stickers: true,
  discounts: true,
  feed_stories: true,
  notification_policy_advanced: true,
};

export type SessionForProductFeatures = {
  organization_id?: string | null;
  entitlement_enforced?: boolean;
  entitlement_keys?: string[];
} | null | undefined;

/**
 * Единая точка: при привязанной организации и включённом enforcement — не расходиться с `core.base` и редакцией.
 * Отдельные SKU (CRM, embed, …) режутся через `require_entitlement` и навигацию, не через этот объект.
 */
export function resolveProductFeatures(session: SessionForProductFeatures): ProductFeatures {
  if (!session?.organization_id) return ALL_ENABLED;
  if (!session.entitlement_enforced) return ALL_ENABLED;

  const keys = new Set(session.entitlement_keys ?? []);
  const hasCore = keys.has("core.base");
  const edition = (import.meta.env.VITE_EDITION ?? "basic").toLowerCase().trim();
  const boxLike = edition === "basic" || edition === "box";
  const stickersOk = hasCore && !boxLike;

  return {
    channels_ui: hasCore,
    integrations_1c: hasCore,
    styling: hasCore,
    stickers: stickersOk,
    discounts: hasCore,
    feed_stories: hasCore,
    notification_policy_advanced: hasCore,
  };
}

/** @deprecated Используйте `resolveProductFeatures` / `useProductFeatures` — не расходятся с SaaS-сессией. */
export const features: ProductFeatures = ALL_ENABLED;

export type Features = ProductFeatures;
