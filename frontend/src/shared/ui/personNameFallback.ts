import i18n from "@/i18n";

function looksLikeUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s).trim());
}

export function displayPersonName(label: string | null | undefined, fallbackId: string): string {
  const n = String(label ?? "").trim();
  if (n) return n;
  const unknown = i18n.t("unknownName", { ns: "common" });
  if (looksLikeUuid(fallbackId)) return unknown;
  return String(fallbackId || "").trim() || unknown;
}
