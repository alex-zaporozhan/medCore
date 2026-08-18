import i18n from "@/i18n";

export function reportsDrillItemTypeLabel(type: string): string {
  switch (type.trim().toLowerCase()) {
    case "lead":
      return i18n.t("drillType.lead", { ns: "reports" });
    case "booking":
      return i18n.t("drillType.booking", { ns: "reports" });
    case "transaction":
      return i18n.t("drillType.transaction", { ns: "reports" });
    default:
      return type;
  }
}
