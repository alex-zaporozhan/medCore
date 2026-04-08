/** Краткоживущий MFA-токен между `/platform/login` и `/platform/login/mfa` (не JWT сессии). */

export const PLATFORM_FOUNDER_MFA_STORAGE_KEY = "dental_booking_platform_founder_mfa_token";

export function getPendingPlatformFounderMfaToken(): string | null {
  try {
    const t = sessionStorage.getItem(PLATFORM_FOUNDER_MFA_STORAGE_KEY)?.trim();
    return t || null;
  } catch {
    return null;
  }
}

export function setPendingPlatformFounderMfaToken(token: string): void {
  try {
    const t = token.trim();
    if (t) sessionStorage.setItem(PLATFORM_FOUNDER_MFA_STORAGE_KEY, t);
    else sessionStorage.removeItem(PLATFORM_FOUNDER_MFA_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function clearPendingPlatformFounderMfaToken(): void {
  try {
    sessionStorage.removeItem(PLATFORM_FOUNDER_MFA_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
