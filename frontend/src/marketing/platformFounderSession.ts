/** localStorage: JWT `platform_founder`, отдельно от админки клиники (ADR-007). */

export const FOUNDER_JWT_STORAGE_KEY = "dental_booking_platform_founder_token";

export function getFounderToken(): string | null {
  try {
    return localStorage.getItem(FOUNDER_JWT_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setFounderToken(token: string): void {
  try {
    const t = token.trim();
    if (t) localStorage.setItem(FOUNDER_JWT_STORAGE_KEY, t);
    else localStorage.removeItem(FOUNDER_JWT_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function clearFounderToken(): void {
  try {
    localStorage.removeItem(FOUNDER_JWT_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
