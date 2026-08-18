import i18n, { type UiLocale } from "@/i18n";

export interface DomainGlossaryEntry {
  ruShort: string;
  enShort: string;
  ruGentle: string;
  enGentle: string;
  ruInside: string;
  enInside: string;
}

const KNOWN_DOMAINS = [
  "all",
  "general",
  "view",
  "manage",
  "run",
  "assign",
  "invite",
  "export",
  "patients",
  "tasks",
  "erp",
  "attribution",
  "booking",
  "ai",
  "omni",
  "leads",
  "rbac",
  "staff",
  "appointments",
  "schedule",
  "patient",
  "finance",
  "billing",
  "payments",
  "crm",
  "notifications",
  "reports",
  "analytics",
  "loyalty",
  "inventory",
  "marketing",
  "integrations",
  "admin",
] as const;

const KNOWN_DOMAIN_SET = new Set<string>(KNOWN_DOMAINS);

const POLICY_KEYS = [
  "allow_patient_disable_discount_notifications",
  "allow_patient_disable_reminders",
  "allow_patient_disable_all_notifications",
  "owner_morning_brief_enabled",
  "morning_brief_send_at_utc",
  "owner_telegram_chat_id",
  "ai_supervisor_enabled",
  "ai_supervisor_send_at_utc",
  "ai_supervisor_recipient_chat_ids",
] as const;

type KnownDomain = (typeof KNOWN_DOMAINS)[number];
type DomainCopyField = "short" | "gentle" | "inside";
type PolicyKey = (typeof POLICY_KEYS)[number];

function domainField(domainKey: KnownDomain, field: DomainCopyField, lng: UiLocale): string {
  return i18n.t(`domains.${domainKey}.${field}`, { ns: "rbac", lng });
}

export function getDomainGlossary(domain: string): DomainGlossaryEntry {
  const key = domain.trim().toLowerCase();
  const label = domain.trim() || key;
  if (!KNOWN_DOMAIN_SET.has(key)) {
    return {
      ruShort: i18n.t("domains.unknown.short", { ns: "rbac", lng: "ru", domain: label }),
      enShort: i18n.t("domains.unknown.short", { ns: "rbac", lng: "en", domain: label }),
      ruGentle: i18n.t("domains.fallback.gentle", { ns: "rbac", lng: "ru" }),
      enGentle: i18n.t("domains.fallback.gentle", { ns: "rbac", lng: "en" }),
      ruInside: i18n.t("domains.fallback.inside", { ns: "rbac", lng: "ru" }),
      enInside: i18n.t("domains.fallback.inside", { ns: "rbac", lng: "en" }),
    };
  }
  const known = key as KnownDomain;
  return {
    ruShort: domainField(known, "short", "ru"),
    enShort: domainField(known, "short", "en"),
    ruGentle: domainField(known, "gentle", "ru"),
    enGentle: domainField(known, "gentle", "en"),
    ruInside: domainField(known, "inside", "ru"),
    enInside: domainField(known, "inside", "en"),
  };
}

export function getDomainPrimaryLabel(domain: string, locale: UiLocale): string {
  const g = getDomainGlossary(domain);
  return locale === "ru" ? g.ruShort : g.enShort;
}

export function getDomainPlainSelectLabel(domain: string, locale: UiLocale): string {
  const primary = getDomainPrimaryLabel(domain, locale);
  if (domain === "all") return primary;
  return `${primary} · ${domain}`;
}

export function getPolicyFieldLabel(key: string, locale: UiLocale): string {
  if (!(POLICY_KEYS as readonly string[]).includes(key)) return key;
  return i18n.t(`policy.${key as PolicyKey}`, { ns: "rbac", lng: locale });
}

export function getRolePresetOptionLabel(code: string): string {
  switch (code) {
    case "manager":
      return i18n.t("presetLabelManager", { ns: "rbac" });
    case "admin":
      return i18n.t("presetLabelAdmin", { ns: "rbac" });
    case "doctor":
      return i18n.t("presetLabelDoctor", { ns: "rbac" });
    default:
      return code;
  }
}

export const rbacTooltipStyles = {
  tooltip: {
    backgroundColor: "var(--mantine-color-body)",
    color: "var(--mantine-color-text)",
    border: "1px solid var(--mantine-color-default-border)",
    boxShadow: "var(--mantine-shadow-md)",
    maxWidth: 440,
  },
} as const;
