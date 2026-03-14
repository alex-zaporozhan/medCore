export interface StoredUtmContext {
  session_id: string;
  utm_source?: string | null;
  utm_medium?: string | null;
  utm_campaign?: string | null;
  utm_content?: string | null;
  utm_term?: string | null;
  landing_page?: string | null;
  anchor?: string | null;
}

const UTM_STORAGE_KEY = "marketing.utm";

function generateSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getCurrentUtm(): StoredUtmContext | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(UTM_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredUtmContext;
    return parsed && parsed.session_id ? parsed : null;
  } catch {
    return null;
  }
}

export function useUtmTracking() {
  if (typeof window === "undefined") return;

  const url = new URL(window.location.href);
  const params = url.searchParams;

  const utm: StoredUtmContext = getCurrentUtm() || {
    session_id: generateSessionId(),
  };

  const hasUtmInUrl =
    params.has("utm_source") ||
    params.has("utm_medium") ||
    params.has("utm_campaign") ||
    params.has("utm_content") ||
    params.has("utm_term");

  if (hasUtmInUrl) {
    utm.utm_source = params.get("utm_source") || undefined;
    utm.utm_medium = params.get("utm_medium") || undefined;
    utm.utm_campaign = params.get("utm_campaign") || undefined;
    utm.utm_content = params.get("utm_content") || undefined;
    utm.utm_term = params.get("utm_term") || undefined;
    utm.landing_page = url.pathname + url.search;
    utm.anchor = url.hash || undefined;
  } else if (!utm.landing_page) {
    utm.landing_page = url.pathname + url.search;
    utm.anchor = url.hash || undefined;
  }

  try {
    window.localStorage.setItem(UTM_STORAGE_KEY, JSON.stringify(utm));
  } catch {
    // ignore storage errors
  }
}

