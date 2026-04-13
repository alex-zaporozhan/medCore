/**
 * Общие утилиты для запросов кабинета основателя (разбор ошибок, безопасный JSON).
 * Сообщения согласованы с `PlatformFounderProvisionQueuePage`.
 */

export async function formatPlatformFounderApiError(r: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await r.json();
    if (body && typeof body === "object") {
      const o = body as { detail?: unknown; code?: unknown };
      const topCode = typeof o.code === "string" ? o.code : "";
      const d = o.detail;
      if (typeof d === "string") {
        return topCode ? `${topCode}: ${d}` : d;
      }
      if (d && typeof d === "object" && "message" in d && typeof (d as { message: string }).message === "string") {
        const nested =
          "code" in d && typeof (d as { code?: string }).code === "string"
            ? `${(d as { code: string }).code}: `
            : "";
        const msg = `${nested}${(d as { message: string }).message}`;
        return topCode ? `${topCode}: ${msg}` : msg;
      }
    }
  } catch {
    /* ignore */
  }
  return fallback;
}

export function parseJsonArray<T>(raw: unknown): T[] {
  return Array.isArray(raw) ? (raw as T[]) : [];
}
