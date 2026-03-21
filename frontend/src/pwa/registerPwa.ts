import { registerSW } from "virtual:pwa-register";

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

  const updateSW = registerSW({
    onNeedRefresh() {
      console.log("[pwa] new version available");
    },
    onOfflineReady() {
      console.log("[pwa] app ready to work offline");
    },
  });

  void updateSW;
}

