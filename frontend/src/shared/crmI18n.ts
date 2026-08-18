import i18n from "@/i18n";

export function crmLeadStatusLabel(status: string): string {
  switch (status) {
    case "open":
    case "success":
    case "lost":
      return i18n.t(`status.${status}`, { ns: "crm" });
    default:
      return status;
  }
}

export function crmRecallChannelLabel(channel: string): string {
  const code = String(channel ?? "").trim().toLowerCase();
  switch (code) {
    case "sms":
    case "telegram":
    case "email":
    case "whatsapp":
      return i18n.t(`retention.channel.${code}`, { ns: "crm" });
    default:
      return channel;
  }
}
