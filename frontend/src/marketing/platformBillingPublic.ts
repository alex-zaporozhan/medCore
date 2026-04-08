/**
 * Публичный контур платформенного биллинга (FE-E1 / 1b-E1).
 * Парсинг ошибок — через `parseFastApiErrorBody` (единый envelope FastAPI из `main.py`).
 */

import { parseFastApiErrorBody } from "@/api/client";

export type PublicCheckoutErrorShape = {
  code: string;
  message: string;
  siteKey: string | null;
  traceId: string | null;
};

const BILLING_MESSAGES: Record<string, string> = {
  captcha_required: "Требуется подтверждение Turnstile. Выполните проверку ниже и снова нажмите «Оплатить».",
  rate_limited: "Слишком много запросов. Подождите немного и попробуйте снова.",
  invalid_email: "Некорректный email.",
  unknown_plan_slug: "Тариф недоступен или отключён.",
  invalid_billing_period: "Некорректный период оплаты.",
  plan_price_missing: "Для выбранного периода у плана нет цены.",
  extra_entitlement_overlaps_plan: "Этот модуль уже входит в выбранный план.",
  extra_entitlement_unknown: "Неизвестное или отключённое дополнение.",
  extra_entitlement_no_price: "У дополнения нет цены в каталоге.",
  yookassa_not_configured: "Платёжный провайдер не настроен на сервере.",
  yookassa_create_failed: "Не удалось создать платёж у провайдера. Попробуйте позже.",
  platform_checkout_return_url_missing: "На сервере не задан URL возврата после оплаты.",
};

export function messageForPlatformCheckoutCode(code: string, fallback: string): string {
  if (code && BILLING_MESSAGES[code]) return BILLING_MESSAGES[code];
  return fallback;
}

export function parsePublicCheckoutFailure(
  status: number,
  data: Record<string, unknown>,
): PublicCheckoutErrorShape {
  const parsed = parseFastApiErrorBody(JSON.stringify(data));
  const code = (parsed.code ?? "").trim();
  let message = (parsed.rawMessage ?? "").trim() || `Ошибка ${status}`;
  const details = parsed.details;
  const siteRaw = details?.site_key;
  const siteKey = typeof siteRaw === "string" ? siteRaw : null;
  const traceId = typeof parsed.traceId === "string" && parsed.traceId.trim() ? parsed.traceId.trim() : null;

  if (code) {
    message = messageForPlatformCheckoutCode(code, message);
  }

  return { code, message, siteKey, traceId };
}
