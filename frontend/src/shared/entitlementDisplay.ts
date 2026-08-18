/**
 * Человекочитаемые подписи для entitlement-ключей (МП §4, Phase0 alignment).
 * Используются в админке: карточка «Подписка и возможности».
 */

import i18n, { tNs } from "@/i18n";

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

function entitlementSlug(key: string): string {
  return key.replaceAll(".", "_");
}

export function labelForEntitlementKey(key: string): EntitlementDisplay {
  const slug = entitlementSlug(key);
  const titleKey = `entitlements.${slug}.title`;
  if (!i18n.exists(titleKey, { ns: "settings" })) {
    return {
      title: key,
      hint: tNs("settings", "entitlements.fallbackHint"),
    };
  }
  return {
    title: tNs("settings", titleKey),
    hint: tNs("settings", `entitlements.${slug}.hint`),
  };
}
