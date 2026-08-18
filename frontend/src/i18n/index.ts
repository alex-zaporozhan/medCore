import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import dayjs from "dayjs";
import "dayjs/locale/en";
import "dayjs/locale/ru";
import enAuth from "./locales/en/auth.json";
import enBookings from "./locales/en/bookings.json";
import enCommon from "./locales/en/common.json";
import enDirectory from "./locales/en/directory.json";
import enNav from "./locales/en/nav.json";
import enSchedule from "./locales/en/schedule.json";
import enChat from "./locales/en/chat.json";
import enCrm from "./locales/en/crm.json";
import enFeed from "./locales/en/feed.json";
import enMoney from "./locales/en/money.json";
import enReports from "./locales/en/reports.json";
import enRbac from "./locales/en/rbac.json";
import enSettings from "./locales/en/settings.json";
import enTasks from "./locales/en/tasks.json";
import ruAuth from "./locales/ru/auth.json";
import ruBookings from "./locales/ru/bookings.json";
import ruCommon from "./locales/ru/common.json";
import ruDirectory from "./locales/ru/directory.json";
import ruNav from "./locales/ru/nav.json";
import ruSchedule from "./locales/ru/schedule.json";
import ruChat from "./locales/ru/chat.json";
import ruCrm from "./locales/ru/crm.json";
import ruFeed from "./locales/ru/feed.json";
import ruMoney from "./locales/ru/money.json";
import ruReports from "./locales/ru/reports.json";
import ruRbac from "./locales/ru/rbac.json";
import ruSettings from "./locales/ru/settings.json";
import ruTasks from "./locales/ru/tasks.json";

export const UI_LOCALE_STORAGE_KEY = "ui.locale";
export type UiLocale = "en" | "ru";

/**
 * Namespaces registered at init. A new ns (A2+) must be added here, in `resources`,
 * as `locales/{en,ru}/<ns>.json`, and in `i18next.d.ts`. Changing fallbackLng /
 * detector / useSuspense is not part of adding a namespace.
 */
export const I18N_NAMESPACES = ["common", "nav", "auth", "schedule", "bookings", "directory", "tasks", "chat", "crm", "money", "reports", "feed", "settings", "rbac"] as const;

export function normalizeUiLocale(lng: string | undefined): UiLocale {
  if (lng && lng.toLowerCase().startsWith("ru")) return "ru";
  return "en";
}

export function readStoredUiLocale(): UiLocale {
  try {
    if (typeof localStorage === "undefined") return "en";
    const raw = localStorage.getItem(UI_LOCALE_STORAGE_KEY);
    if (raw === "en" || raw === "ru") return raw;
  } catch {
    return "en";
  }
  return "en";
}

export function persistUiLocale(locale: UiLocale): void {
  try {
    localStorage.setItem(UI_LOCALE_STORAGE_KEY, locale);
  } catch {
    // private mode / quota — locale still applies in memory
  }
}

export function syncDayjsLocale(locale: UiLocale): void {
  dayjs.locale(locale);
}

function applyDayjsFromI18n(lng: string | undefined): void {
  syncDayjsLocale(normalizeUiLocale(lng));
}

function cloneResource<T>(value: T): T {
  return structuredClone(value);
}

void i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        common: cloneResource(enCommon),
        nav: cloneResource(enNav),
        auth: cloneResource(enAuth),
        schedule: cloneResource(enSchedule),
        bookings: cloneResource(enBookings),
        directory: cloneResource(enDirectory),
        tasks: cloneResource(enTasks),
        chat: cloneResource(enChat),
        crm: cloneResource(enCrm),
        money: cloneResource(enMoney),
        reports: cloneResource(enReports),
        feed: cloneResource(enFeed),
        settings: cloneResource(enSettings),
        rbac: cloneResource(enRbac),
      },
      ru: {
        common: cloneResource(ruCommon),
        nav: cloneResource(ruNav),
        auth: cloneResource(ruAuth),
        schedule: cloneResource(ruSchedule),
        bookings: cloneResource(ruBookings),
        directory: cloneResource(ruDirectory),
        tasks: cloneResource(ruTasks),
        chat: cloneResource(ruChat),
        crm: cloneResource(ruCrm),
        money: cloneResource(ruMoney),
        reports: cloneResource(ruReports),
        feed: cloneResource(ruFeed),
        settings: cloneResource(ruSettings),
        rbac: cloneResource(ruRbac),
      },
    },
    lng: readStoredUiLocale(),
    fallbackLng: "en",
    supportedLngs: ["en", "ru"],
    load: "languageOnly",
    defaultNS: "common",
    ns: [...I18N_NAMESPACES],
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
    initAsync: false,
  })
  .then(() => {
    applyDayjsFromI18n(i18n.language);
  })
  .catch((err: unknown) => {
    console.error("i18n init failed", err);
  });

applyDayjsFromI18n(i18n.language || readStoredUiLocale());

i18n.on("languageChanged", (lng: string) => {
  applyDayjsFromI18n(lng);
});

export type I18nNamespace = (typeof I18N_NAMESPACES)[number];

/** Dynamic key (suffix from API/status) — typed ParseKeys overloads treat options as defaultValue. */
export function tNs(ns: I18nNamespace, key: string): string {
  return String(i18n.t(key as never, { ns }));
}

export default i18n;
