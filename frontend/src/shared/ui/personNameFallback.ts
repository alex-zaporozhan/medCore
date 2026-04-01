function looksLikeUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s).trim());
}

export function displayPersonName(label: string | null | undefined, fallbackId: string): string {
  const n = String(label ?? "").trim();
  if (n) return n;
  if (looksLikeUuid(fallbackId)) return "Имя неизвестно";
  return String(fallbackId || "").trim() || "Имя неизвестно";
}

