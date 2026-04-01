import { registerSW } from "virtual:pwa-register";

/** Событие: доступна новая сборка PWA (пациентское `/app` показывает баннер). */
export const PWA_NEED_REFRESH = "dental-pwa-need-refresh";

/** Кэш shell готов — можно кратко подсказать (не блокируем UI). */
export const PWA_OFFLINE_READY = "dental-pwa-offline-ready";

let activateNewServiceWorker: (() => void) | null = null;

/** Активировать ожидающий SW и перезагрузить страницу (после `onNeedRefresh`). */
export function applyPwaUpdate(): void {
  activateNewServiceWorker?.();
}

export function registerPwa(): void {
  if (typeof window === "undefined") {
    return;
  }

  if (!("serviceWorker" in navigator)) {
    return;
  }

  if (!import.meta.env.PROD) {
    return;
  }

  activateNewServiceWorker = registerSW({
    onNeedRefresh() {
      window.dispatchEvent(new Event(PWA_NEED_REFRESH));
    },
    onOfflineReady() {
      window.dispatchEvent(new Event(PWA_OFFLINE_READY));
    },
  });
}
