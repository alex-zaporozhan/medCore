import "i18next";
import type enAuth from "./locales/en/auth.json";
import type enBookings from "./locales/en/bookings.json";
import type enCommon from "./locales/en/common.json";
import type enDirectory from "./locales/en/directory.json";
import type enNav from "./locales/en/nav.json";
import type enSchedule from "./locales/en/schedule.json";
import type enChat from "./locales/en/chat.json";
import type enCrm from "./locales/en/crm.json";
import type enFeed from "./locales/en/feed.json";
import type enMoney from "./locales/en/money.json";
import type enReports from "./locales/en/reports.json";
import type enRbac from "./locales/en/rbac.json";
import type enSettings from "./locales/en/settings.json";
import type enTasks from "./locales/en/tasks.json";

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "common";
    resources: {
      common: typeof enCommon;
      nav: typeof enNav;
      auth: typeof enAuth;
      schedule: typeof enSchedule;
      bookings: typeof enBookings;
      directory: typeof enDirectory;
      tasks: typeof enTasks;
      chat: typeof enChat;
      crm: typeof enCrm;
      money: typeof enMoney;
      reports: typeof enReports;
      feed: typeof enFeed;
      settings: typeof enSettings;
      rbac: typeof enRbac;
    };
  }
}
