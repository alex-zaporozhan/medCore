import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { isAdminChromePath } from "@/shared/errors";
import i18n, {
  persistUiLocale,
  UI_LOCALE_STORAGE_KEY,
  normalizeUiLocale,
  type UiLocale,
} from "./index";

/** Matches `index.html` this wave. Marketing/PWA are not on `ui.locale` yet. */
export const PUBLIC_HTML_LANG = "ru";

export function isAdminPath(pathname?: string): boolean {
  return isAdminChromePath(
    pathname ?? (typeof window === "undefined" ? "" : window.location.pathname),
  );
}

export function applyDocumentLang(locale: UiLocale, pathname?: string): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = isAdminPath(pathname) ? locale : PUBLIC_HTML_LANG;
}

type HistoryStateFn = typeof history.pushState;

let historyPatched = false;
let origPushState: HistoryStateFn | null = null;
let origReplaceState: HistoryStateFn | null = null;
const pathListeners = new Set<() => void>();

function notifyPathListeners(): void {
  pathListeners.forEach((listener) => {
    try {
      listener();
    } catch (err: unknown) {
      console.error("ui locale path listener failed", err);
    }
  });
}

function ensureHistoryPatch(): void {
  if (typeof window === "undefined" || historyPatched) return;
  historyPatched = true;
  origPushState = history.pushState.bind(history);
  origReplaceState = history.replaceState.bind(history);
  history.pushState = function pushStatePatched(
    this: History,
    ...args: Parameters<HistoryStateFn>
  ) {
    origPushState!.apply(this, args);
    notifyPathListeners();
  };
  history.replaceState = function replaceStatePatched(
    this: History,
    ...args: Parameters<HistoryStateFn>
  ) {
    origReplaceState!.apply(this, args);
    notifyPathListeners();
  };
  window.addEventListener("popstate", notifyPathListeners);
}

function subscribeHistoryPath(listener: () => void): () => void {
  ensureHistoryPatch();
  pathListeners.add(listener);
  return () => {
    pathListeners.delete(listener);
  };
}

export function useUiLocale(): { locale: UiLocale; setLocale: (next: UiLocale) => void } {
  const { i18n: i18nInstance } = useTranslation();
  const locale = normalizeUiLocale(i18nInstance.language);

  const setLocale = useCallback((next: UiLocale) => {
    persistUiLocale(next);
    void i18nInstance.changeLanguage(next).catch((err: unknown) => {
      console.error("i18n changeLanguage failed", { locale: next, err });
    });
    applyDocumentLang(next);
  }, [i18nInstance]);

  useEffect(() => {
    applyDocumentLang(locale);
  }, [locale]);

  useEffect(() => {
    return subscribeHistoryPath(() => {
      applyDocumentLang(normalizeUiLocale(i18n.language));
    });
  }, []);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== null && event.key !== UI_LOCALE_STORAGE_KEY) return;
      const next = event.newValue === "en" || event.newValue === "ru" ? event.newValue : "en";
      if (normalizeUiLocale(i18n.language) === next) {
        applyDocumentLang(next);
        return;
      }
      void i18n.changeLanguage(next).catch((err: unknown) => {
        console.error("i18n changeLanguage from storage failed", { locale: next, err });
      });
      applyDocumentLang(next);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { locale, setLocale };
}

export type { UiLocale };

/** Mount once under I18nextProvider so persist/storage/document.lang run without a switcher. */
export function UiLocaleSync() {
  useUiLocale();
  return null;
}
