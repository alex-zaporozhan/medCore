import i18n from "@/i18n";

const CHANNEL_TYPE_CODES = [
  "TELEGRAM_BOT",
  "WHATSAPP_BUSINESS",
  "VIBER_BOT",
  "VK_BOT",
  "MAX_CHAT",
  "SMS_GATEWAY",
  "EMAIL_INBOX",
  "OTHER",
] as const;

const CHANNEL_STATUS_CODES = ["PENDING_SETUP", "ACTIVE", "DISABLED", "ERROR"] as const;

export function adminChatMessagesRegion(): {
  component: "section";
  "aria-label": string;
} {
  return {
    component: "section",
    "aria-label": i18n.t("region.messages", { ns: "chat" }),
  };
}

export function omniChannelTypeLabel(type: string): string {
  const code = type.toUpperCase();
  switch (code) {
    case "TELEGRAM_BOT":
    case "WHATSAPP_BUSINESS":
    case "VIBER_BOT":
    case "VK_BOT":
    case "MAX_CHAT":
    case "SMS_GATEWAY":
    case "EMAIL_INBOX":
    case "OTHER":
      return i18n.t(`channelType.${code}`, { ns: "chat" });
    default:
      return type;
  }
}

export function omniChannelStatusLabel(status: string): string {
  const code = status.toUpperCase();
  switch (code) {
    case "PENDING_SETUP":
    case "ACTIVE":
    case "DISABLED":
    case "ERROR":
      return i18n.t(`channelStatus.${code}`, { ns: "chat" });
    default:
      return status;
  }
}

export function omniAiModeLabel(mode: string): string {
  const code = mode.toUpperCase();
  switch (code) {
    case "DISABLED":
    case "AUTO_REPLY":
    case "SUGGEST_ONLY":
      return i18n.t(`aiMode.${code}`, { ns: "chat" });
    default:
      return mode;
  }
}

export function omniChannelTypeOptions(): { value: string; label: string }[] {
  return CHANNEL_TYPE_CODES.map((value) => ({ value, label: omniChannelTypeLabel(value) }));
}

export function omniChannelStatusOptions(): { value: string; label: string }[] {
  return CHANNEL_STATUS_CODES.map((value) => ({ value, label: omniChannelStatusLabel(value) }));
}

export function vaultPresetLabel(id: string, fallback: string): string {
  switch (id) {
    case "tax":
      return i18n.t("vault.presetTax", { ns: "chat" });
    case "vip_sleep":
      return i18n.t("vault.presetVipSleep", { ns: "chat" });
    case "consumables":
      return i18n.t("vault.presetConsumables", { ns: "chat" });
    default:
      return fallback;
  }
}
