/**
 * Публичная отправка заявок POST /api/v1/platform-leads/ (Turnstile как на checkout).
 */

import { parsePublicCheckoutFailure } from "@/marketing/platformBillingPublic";

export type EnterpriseLeadSubmitErrorShape = {
  code: string;
  message: string;
  siteKey: string | null;
  traceId: string | null;
};

export function parseEnterpriseLeadSubmitFailure(
  status: number,
  bodyText: string,
): EnterpriseLeadSubmitErrorShape {
  let data: Record<string, unknown> = {};
  try {
    data = JSON.parse(bodyText) as Record<string, unknown>;
  } catch {
    /* ignore */
  }
  const base = parsePublicCheckoutFailure(status, data);
  if (base.code === "captcha_required") {
    return {
      ...base,
      message:
        "Требуется подтверждение Turnstile. Выполните проверку ниже и снова отправьте форму.",
    };
  }
  if (base.code === "rate_limited") {
    return {
      ...base,
      message: "Слишком много попыток. Подождите немного и повторите отправку.",
    };
  }
  return base;
}
