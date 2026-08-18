import i18n from "@/i18n";

export function settingsRoleLabel(role: string): string {
  switch (role) {
    case "owner":
    case "manager":
    case "admin":
    case "doctor":
      return i18n.t(`roles.${role}`, { ns: "settings" });
    default:
      return role;
  }
}

export function settingsPriorityLabel(level: string): string {
  switch (level) {
    case "normal":
    case "priority":
    case "critical":
      return i18n.t(`priority.${level}`, { ns: "settings" });
    default:
      return level;
  }
}

export function settingsAiIntentLabel(intent: string): string {
  switch (intent) {
    case "schedule":
    case "location":
    case "faq":
    case "booking_change":
    case "price_info":
      return i18n.t(`ai.intent.${intent}`, { ns: "settings" });
    default:
      return intent;
  }
}

export function settingsAiModeLabel(mode: string): string {
  switch (mode) {
    case "draft_only":
    case "safe_autoreply":
    case "analytics_only":
      return i18n.t(`ai.mode.${mode}`, { ns: "settings" });
    default:
      return mode;
  }
}

export function settingsAiStatusLine(mode: string): string {
  switch (mode) {
    case "external_active":
    case "fallback_local":
    case "disabled":
      return i18n.t(`ai.status.${mode}`, { ns: "settings" });
    default:
      return i18n.t("ai.status.disabled", { ns: "settings" });
  }
}

const ROLE_VALUES = ["owner", "manager", "admin", "doctor"] as const;
const PRIORITY_VALUES = ["normal", "priority", "critical"] as const;
const AI_INTENT_VALUES = ["schedule", "location", "faq", "booking_change", "price_info"] as const;
const AI_MODE_VALUES = ["draft_only", "safe_autoreply", "analytics_only"] as const;

export function settingsRoleOptions(): { value: string; label: string }[] {
  return ROLE_VALUES.map((value) => ({ value, label: settingsRoleLabel(value) }));
}

export function settingsPriorityOptions(): { value: string; label: string }[] {
  return PRIORITY_VALUES.map((value) => ({ value, label: settingsPriorityLabel(value) }));
}

export function settingsAiIntentOptions(): { value: string; label: string }[] {
  return AI_INTENT_VALUES.map((value) => ({ value, label: settingsAiIntentLabel(value) }));
}

export function settingsAiModeOptions(): { value: string; label: string }[] {
  return AI_MODE_VALUES.map((value) => ({ value, label: settingsAiModeLabel(value) }));
}

export function settingsFormStatusLabel(status: string): string {
  switch (status) {
    case "draft":
    case "issued":
    case "in_progress":
    case "signed":
    case "cancelled":
    case "expired":
    case "revoked":
    case "unknown":
      return i18n.t(`forms.status.${status}`, { ns: "settings" });
    default:
      return status;
  }
}

export function settingsFormSubmittedByLabel(who: string): string {
  switch (who) {
    case "patient":
    case "admin":
    case "doctor":
    case "system":
      return i18n.t(`forms.submittedBy.${who}`, { ns: "settings" });
    default:
      return who;
  }
}
