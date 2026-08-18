import i18n from "@/i18n";

export function feedRevenuePeriodLabel(period: string | undefined): string {
  switch (period) {
    case "night":
    case "day":
    case "week":
      return i18n.t(`period.${period}`, { ns: "feed" });
    default:
      return i18n.t("period.night", { ns: "feed" });
  }
}
