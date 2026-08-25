import { afterEach, describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dayjs from "dayjs";
import i18n, { readStoredUiLocale, UI_LOCALE_STORAGE_KEY } from "../index";
import { taskStatusLabel } from "@/shared/taskStatusI18n";
import { adminChatMessagesRegion, omniChannelCreateTypeOptions, omniChannelTypeLabel, isOmniChannelCreatableType } from "@/shared/chatI18n";
import { crmLeadStatusLabel, crmRecallChannelLabel } from "@/shared/crmI18n";
import { moneyCashboxTypeLabel, moneyDiscountTypeLabel, moneyFinanceTxSourceLabel, moneyFinanceTxTypeLabel, moneyGatewayLabel, moneyInventoryTxTypeLabel, moneyLoyaltyPackageKindLabel, moneyPassStatusLabel, moneySalaryTxTypeLabel, moneyWalletTxTypeLabel } from "@/shared/moneyI18n";
import { feedRevenuePeriodLabel } from "@/shared/feedI18n";
import { reportsDrillItemTypeLabel } from "@/shared/reportsI18n";
import {
  getDomainPrimaryLabel,
  getPolicyFieldLabel,
  getRolePresetOptionLabel,
} from "@/shared/rbacI18n";
import {
  settingsAiIntentLabel,
  settingsAiModeLabel,
  settingsAiStatusLine,
  settingsFormStatusLabel,
  settingsFormSubmittedByLabel,
  settingsPriorityLabel,
  settingsRoleLabel,
} from "@/shared/settingsI18n";
import { displayPersonName } from "@/shared/ui/personNameFallback";
import { labelForEntitlementKey } from "@/shared/entitlementDisplay";
import { commonErrorI18nKey, isAdminChromePath } from "@/shared/errors";
import enAuth from "../locales/en/auth.json";
import enBookings from "../locales/en/bookings.json";
import enCommon from "../locales/en/common.json";
import enDirectory from "../locales/en/directory.json";
import enNav from "../locales/en/nav.json";
import enSchedule from "../locales/en/schedule.json";
import enTasks from "../locales/en/tasks.json";
import enChat from "../locales/en/chat.json";
import enCrm from "../locales/en/crm.json";
import enFeed from "../locales/en/feed.json";
import enMoney from "../locales/en/money.json";
import enReports from "../locales/en/reports.json";
import enSettings from "../locales/en/settings.json";
import enRbac from "../locales/en/rbac.json";
import { marketingPlanCopy } from "@/marketing/marketingPublicPlans";
import enMarketing from "../locales/en/marketing.json";
import enPatient from "../locales/en/patient.json";
import enFounder from "../locales/en/founder.json";
import ruAuth from "../locales/ru/auth.json";
import ruBookings from "../locales/ru/bookings.json";
import ruCommon from "../locales/ru/common.json";
import ruDirectory from "../locales/ru/directory.json";
import ruNav from "../locales/ru/nav.json";
import ruSchedule from "../locales/ru/schedule.json";
import ruTasks from "../locales/ru/tasks.json";
import ruChat from "../locales/ru/chat.json";
import ruCrm from "../locales/ru/crm.json";
import ruFeed from "../locales/ru/feed.json";
import ruMoney from "../locales/ru/money.json";
import ruReports from "../locales/ru/reports.json";
import ruSettings from "../locales/ru/settings.json";
import ruRbac from "../locales/ru/rbac.json";
import ruMarketing from "../locales/ru/marketing.json";
import ruPatient from "../locales/ru/patient.json";
import ruFounder from "../locales/ru/founder.json";

function leafKeys(value: unknown, prefix = ""): string[] {
  if (value !== null && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nested]) =>
      leafKeys(nested, prefix ? `${prefix}.${key}` : key),
    );
  }
  return prefix ? [prefix] : [];
}

describe("i18n default locale", () => {
  afterEach(async () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    await i18n.changeLanguage("en");
    dayjs.locale("en");
  });

  it("readStoredUiLocale returns en when ui.locale is absent", () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    expect(readStoredUiLocale()).toBe("en");
  });

  it("readStoredUiLocale returns ru when ui.locale is ru", () => {
    localStorage.setItem(UI_LOCALE_STORAGE_KEY, "ru");
    expect(readStoredUiLocale()).toBe("ru");
  });

  it("initialized language is en when storage has no ui.locale", () => {
    expect(localStorage.getItem(UI_LOCALE_STORAGE_KEY)).toBeNull();
    expect(i18n.language.startsWith("en")).toBe(true);
  });

  it("common.save resolves to EN chrome", () => {
    expect(i18n.t("save")).toBe("Save");
  });

  it("auth clinic login heading is EN by default", () => {
    expect(i18n.t("clinic.pageTitle", { ns: "auth" })).toBe("Clinic staff sign-in");
  });

  it("auth public and founder login headings are EN by default", () => {
    expect(i18n.t("public.pageTitle", { ns: "auth" })).toBe("Sign in");
    expect(i18n.t("founder.pageTitle", { ns: "auth" })).toBe("Platform founder");
    expect(i18n.t("founder.navOverview", { ns: "auth" })).toBe("Overview");
    expect(i18n.t("founder.navProvision", { ns: "auth" })).toBe("Provision queue");
  });

  it("AdminLayout source has no Russian string literals", () => {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const srcPath = path.resolve(here, "../../admin/layouts/AdminLayout.tsx");
    const src = fs
      .readFileSync(srcPath, "utf8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    expect(src).not.toMatch(/["'`][^"'`\n]*[А-Яа-яЁё]/);
  });

  it("nav feed item is EN by default", () => {
    expect(i18n.t("items.feed", { ns: "nav" })).toBe("Feed");
  });

  it("auth password min hint uses plural count", () => {
    expect(i18n.t("clinic.passwordMinHint", { ns: "auth", count: 8 })).toBe("At least 8 characters");
    expect(i18n.t("clinic.passwordMinError", { ns: "auth", count: 8 })).toBe(
      "Password must be at least 8 characters",
    );
  });

  it("schedule remainingVisits uses plural count", () => {
    expect(i18n.t("bookings.remainingVisits", { ns: "schedule", count: 1 })).toBe("1 visit remaining");
    expect(i18n.t("bookings.remainingVisits", { ns: "schedule", count: 2 })).toBe("2 visits remaining");
  });

  it("waitlist and recall enums are dictionary chrome, not API tokens", () => {
    expect(i18n.t("waitlistPage.waiting", { ns: "schedule" })).toBe("Waiting");
    expect(i18n.t("recall.campaignDraft", { ns: "schedule" })).toBe("Draft");
    expect(i18n.t("recall.daysAfterVisit", { ns: "schedule" })).toBe("N days after visit");
  });

  it("directory patients title is EN by default", () => {
    expect(i18n.t("patients.title", { ns: "directory" })).toBe("Patients");
    expect(i18n.t("staff.title", { ns: "directory" })).toBe("Staff");
    expect(i18n.t("staff.cardTitle", { ns: "directory" })).toBe("Staff member");
    expect(i18n.t("clinics.emptyTitle", { ns: "directory" })).toBe("No clinics yet");
    expect(i18n.t("clinics.types.stomatology", { ns: "directory" })).toBe("Dentistry");
  });

  it("chat omni chrome is EN by default", () => {
    expect(i18n.t("staff.title", { ns: "chat" })).toBe("Team chat");
    expect(i18n.t("staff.fallbackTitle", { ns: "chat" })).toBe("Staff chat");
    expect(i18n.t("region.messages", { ns: "chat" })).toBe("Conversation messages");
    expect(i18n.t("omni.claim", { ns: "chat" })).toBe("Claim");
    expect(i18n.t("errors.claimFailed", { ns: "chat" })).toBe("Could not claim the ticket");
    expect(i18n.t("errors.saveFailed", { ns: "chat" })).toBe("Could not save");
    expect(i18n.t("errors.noConversation", { ns: "chat" })).toBe("no conversation");
    expect(i18n.t("errors.fileTypeDenied", { ns: "chat" })).toBe("This file type is not allowed");
    expect(i18n.t("errors.fileEmpty", { ns: "chat" })).toBe("The file is empty");
    expect(i18n.t("errors.fileSvgForbidden", { ns: "chat" })).toBe("SVG files are not allowed");
    expect(omniChannelTypeLabel("VK_BOT")).toBe("VK bot");
    expect(omniChannelCreateTypeOptions().some((o) => o.value === "VK_BOT")).toBe(false);
    expect(isOmniChannelCreatableType("VK_BOT")).toBe(false);
    expect(isOmniChannelCreatableType("telegram_bot")).toBe(true);
    expect(i18n.t("omniChannels.intro", { ns: "chat" })).not.toMatch(/\bVK\b/i);
    expect(omniChannelTypeLabel("not_a_channel")).toBe("not_a_channel");
    expect(adminChatMessagesRegion()["aria-label"]).toBe("Conversation messages");
    expect(i18n.t("unknownName", { ns: "common" })).toBe("Unknown name");
    expect(displayPersonName(null, "00000000-0000-0000-0000-000000000001")).toBe("Unknown name");
  });

  it("tasks title and stream chrome are EN by default", () => {
    expect(i18n.t("title", { ns: "tasks" })).toBe("Tasks");
    expect(i18n.t("streams.all", { ns: "tasks" })).toBe("All streams");
    expect(i18n.t("leadsTitle", { ns: "tasks" })).toBe("Leads (log)");
    expect(i18n.t("status.open", { ns: "tasks" })).toBe("Open");
    expect(i18n.t("card.claim", { ns: "tasks" })).toBe("Claim");
    expect(i18n.t("card.ai", { ns: "tasks" })).toBe("AI");
    expect(taskStatusLabel("open")).toBe("Open");
    expect(taskStatusLabel("unknown_status")).toBe("unknown_status");
  });

  it("crm pipeline chrome is EN by default", () => {
    expect(i18n.t("pipeline.title", { ns: "crm" })).toBe("Sales pipeline");
    expect(i18n.t("pipeline.emptyPipelinesTitle", { ns: "crm" })).toBe("No pipelines yet");
    expect(i18n.t("pipeline.aiToolUnavailable", { ns: "crm" })).toBe(
      "Not enough permissions or the backend tool is unavailable.",
    );
    expect(crmLeadStatusLabel("open")).toBe("Open");
    expect(crmLeadStatusLabel("success")).toBe("Won");
    expect(crmLeadStatusLabel("lost")).toBe("Lost");
    expect(crmLeadStatusLabel("unknown_status")).toBe("unknown_status");
    expect(crmRecallChannelLabel("sms")).toBe("SMS");
    expect(crmRecallChannelLabel("WHATSAPP")).toBe("WhatsApp");
    expect(crmRecallChannelLabel("carrier-pigeon")).toBe("carrier-pigeon");
  });

  it("money finance title is EN by default", () => {
    expect(i18n.t("finance.title", { ns: "money" })).toBe("Finance and ERP");
    expect(i18n.t("discounts.title", { ns: "money" })).toBe("Discounts and promotions");
    expect(i18n.t("gateway.yookassa", { ns: "money" })).toBe("YooKassa");
    expect(i18n.t("finance.txType.income", { ns: "money" })).toBe("Income");
    expect(i18n.t("loyalty.needPatientId", { ns: "money" })).toBe(
      "Paste a patient UUID above to look up passes.",
    );
    expect(i18n.t("commerce.deleteLocTitle", { ns: "money" })).toBe("Delete location");
    expect(moneyCashboxTypeLabel("cash")).toBe("Cash");
    expect(moneyCashboxTypeLabel("unknown_box")).toBe("unknown_box");
    expect(moneyDiscountTypeLabel("first_visit")).toBe("First visit");
    expect(moneyGatewayLabel("yookassa")).toBe("YooKassa");
    expect(moneyGatewayLabel("not_a_gw")).toBe("not_a_gw");
    expect(moneyFinanceTxTypeLabel("income")).toBe("Income");
    expect(moneyFinanceTxTypeLabel("mystery")).toBe("mystery");
    expect(moneySalaryTxTypeLabel("accrual")).toBe("Accrual");
    expect(moneyInventoryTxTypeLabel("outgoing")).toBe("Outgoing");
    expect(moneyFinanceTxSourceLabel("acquiring")).toBe("Acquiring");
    expect(moneyLoyaltyPackageKindLabel("visits")).toBe("Visit pack");
    expect(moneyWalletTxTypeLabel("earn")).toBe("Earn");
    expect(moneyPassStatusLabel("used_up")).toBe("Used up");
  });

  it("feed and reports chrome is EN by default", () => {
    expect(i18n.t("title", { ns: "feed" })).toBe("Feed");
    expect(i18n.t("newPost", { ns: "feed" })).toBe("New post");
    expect(i18n.t("composeAria", { ns: "feed" })).toBe("Create a clinic feed post");
    expect(i18n.t("publish", { ns: "feed" })).toBe("Publish");
    expect(i18n.t("filesQueued", { ns: "feed", count: 1 })).toBe("1 file (uploaded after publish)");
    expect(i18n.t("filesQueued", { ns: "feed", count: 2 })).toBe("2 files (uploaded after publish)");
    expect(i18n.t("titleFull", { ns: "reports" })).toBe("Reports and dashboard");
    expect(i18n.t("trafficSource", { ns: "reports" })).toBe("Traffic source");
    expect(i18n.t("attributionTitle", { ns: "reports" })).toBe(
      "Marketing and attribution (click a row for drill-down)",
    );
    expect(i18n.t("aiTitle", { ns: "reports" })).toBe("AI conflict reports");
    expect(i18n.t("advisorTitle", { ns: "reports" })).toBe("AI Marketing Advisor");
    expect(i18n.t("noShowRateLine", { ns: "reports", rate: "12.5" })).toBe("No-show: 12.5%");
    expect(reportsDrillItemTypeLabel("lead")).toBe("Lead");
    expect(reportsDrillItemTypeLabel("booking")).toBe("Booking");
    expect(reportsDrillItemTypeLabel("mystery")).toBe("mystery");
    expect(feedRevenuePeriodLabel("day")).toBe("today");
    expect(feedRevenuePeriodLabel("week")).toBe("this week");
    expect(feedRevenuePeriodLabel("night")).toBe("overnight");
    expect(feedRevenuePeriodLabel("not-a-period")).toBe("overnight");
    expect(feedRevenuePeriodLabel(undefined)).toBe("overnight");
  });

  it("marketing landing chrome is EN by default", () => {
    expect(i18n.t("hero.title", { ns: "marketing" })).toBe("The operating system for growing your business");
    expect(i18n.t("header.patientApp", { ns: "marketing" })).toBe("Patient app");
    expect(i18n.t("header.signIn", { ns: "marketing" })).toBe("Sign in");
    expect(i18n.t("signup.title", { ns: "marketing" })).toBe("Register your organization");
    expect(i18n.t("checkout.subscribe", { ns: "marketing" })).toBe("Subscribe");
    expect(i18n.t("htmlTitle", { ns: "marketing" })).toBe("MedCore — clinic operating system");
    expect(i18n.t("invite.title", { ns: "marketing" })).toBe("Owner invitation");
    expect(marketingPlanCopy("start").headline).toBe("Start");
    expect(marketingPlanCopy("growth").headline).toBe("Growth");
  });

  it("settings chrome is EN by default", () => {
    expect(i18n.t("hub.title", { ns: "settings" })).toBe("Settings");
    expect(i18n.t("subscription.title", { ns: "settings" })).toBe("Platform subscription");
    expect(i18n.t("forms.title", { ns: "settings" })).toBe("Forms and documents");
    expect(i18n.t("emergency.title", { ns: "settings" })).toBe("Announcement wall");
    expect(i18n.t("ai.title", { ns: "settings" })).toBe("AI and assistant");
    expect(i18n.t("embed.secretIssued", { ns: "settings", prefix: "abc" })).toBe(
      "issued (prefix abc…)",
    );
    expect(settingsRoleLabel("owner")).toBe("Owner");
    expect(settingsRoleLabel("not-a-role")).toBe("not-a-role");
    expect(settingsPriorityLabel("critical")).toBe("Critical");
    expect(settingsAiIntentLabel("schedule")).toBe("Schedule");
    expect(settingsAiModeLabel("draft_only")).toBe("Drafts only");
    expect(settingsAiStatusLine("external_active")).toBe(
      "AI is connected (external provider active).",
    );
    expect(settingsAiStatusLine("mystery")).toBe("AI is off.");
    expect(settingsFormStatusLabel("signed")).toBe("Signed");
    expect(settingsFormStatusLabel("not-a-status")).toBe("not-a-status");
    expect(settingsFormSubmittedByLabel("patient")).toBe("Patient");
    expect(settingsFormSubmittedByLabel("mystery")).toBe("mystery");
    expect(i18n.t("pageTitle", { ns: "rbac" })).toBe("Access rights & policies");
    expect(i18n.t("announcements.title", { ns: "rbac" })).toBe("Announcement publish rights");
    expect(getDomainPrimaryLabel("all", "en")).toBe("All domains");
    expect(getDomainPrimaryLabel("all", "ru")).toBe("Все домены");
    expect(getDomainPrimaryLabel("view", "en")).toBe("View (code prefix)");
    expect(getDomainPrimaryLabel("mystery-domain", "en")).toContain("mystery-domain");
    expect(getPolicyFieldLabel("owner_telegram_chat_id", "en")).toBe("Owner Telegram chat ID");
    expect(getPolicyFieldLabel("not-a-policy", "en")).toBe("not-a-policy");
    expect(getRolePresetOptionLabel("manager")).toBe("Like system role “Manager”");
    expect(getRolePresetOptionLabel("mystery")).toBe("mystery");
    expect(i18n.t("criticalSelfRoleMsg", { ns: "rbac", roles: "owner" })).toContain("owner");
    expect(i18n.t("saveFailed", { ns: "rbac" })).toBe("Could not save changes");
    expect(labelForEntitlementKey("core.base").title).toBe("Product base");
    expect(labelForEntitlementKey("mystery.key").title).toBe("mystery.key");
    expect(labelForEntitlementKey("mystery.key").hint).toBe("Platform option");
    expect(i18n.t("errors.crashTitle", { ns: "common" })).toBe("Something went wrong");
    expect(i18n.t("errors.entitlement_required", { ns: "common" })).toMatch(/plan/i);
    expect(i18n.t("errors.method_not_allowed", { ns: "common" })).toMatch(/method/i);
    expect(i18n.t("dialogClose", { ns: "common" })).toBe("Close");
    expect(labelForEntitlementKey("core.base").hint).toMatch(/Bookings/i);
    expect(commonErrorI18nKey("entitlement_required")).toBe("errors.entitlement_required");
    expect(commonErrorI18nKey("invalid_credentials")).toBe("errors.invalid_credentials");
    expect(i18n.t("errors.invalid_credentials", { ns: "common" })).toMatch(/invalid email or password/i);
    expect(commonErrorI18nKey("billing_revoked")).toBe("errors.billing_revoked");
    expect(i18n.t("errors.billing_revoked", { ns: "common" })).toMatch(/subscription/i);
    expect(commonErrorI18nKey("not-a-code")).toBeNull();
    expect(isAdminChromePath("/admin/settings")).toBe(true);
    expect(isAdminChromePath("/app/chat")).toBe(false);
  });

  it("rbac ru empty catalog note does not fall back to EN; no Diff jargon", async () => {
    await i18n.changeLanguage("ru");
    expect(i18n.t("catalogDescriptionLanguageNote", { ns: "rbac" })).toBe("");
    expect(i18n.t("diffRole", { ns: "rbac" })).not.toMatch(/Diff before save/i);
  });

  it("booking status awaiting_payment is EN, not occupied", () => {
    expect(i18n.t("status.awaiting_payment", { ns: "bookings" })).toBe("Awaiting payment");
    expect(i18n.t("status.occupied", { ns: "bookings" })).toBe("Busy");
  });

  it("missing ru key falls back to en, not a JSX leftover", async () => {
    i18n.addResource("en", "common", "auditFallbackOnly", "From English");
    await i18n.changeLanguage("ru");
    // Test-only key is not in the typed dictionary.
    expect(i18n.t("auditFallbackOnly" as never)).toBe("From English");
  });
});

describe("dictionary key parity", () => {
  it("common en/ru keys match", () => {
    expect(leafKeys(ruCommon).sort()).toEqual(leafKeys(enCommon).sort());
  });

  it("nav en/ru keys match", () => {
    expect(leafKeys(ruNav).sort()).toEqual(leafKeys(enNav).sort());
  });

  it("auth en/ru keys match", () => {
    expect(leafKeys(ruAuth).sort()).toEqual(leafKeys(enAuth).sort());
  });

  it("schedule en/ru keys match", () => {
    expect(leafKeys(ruSchedule).sort()).toEqual(leafKeys(enSchedule).sort());
  });

  it("bookings en/ru keys match", () => {
    expect(leafKeys(ruBookings).sort()).toEqual(leafKeys(enBookings).sort());
  });

  it("directory en/ru keys match", () => {
    expect(leafKeys(ruDirectory).sort()).toEqual(leafKeys(enDirectory).sort());
  });

  it("tasks en/ru keys match", () => {
    expect(leafKeys(ruTasks).sort()).toEqual(leafKeys(enTasks).sort());
  });

  it("chat en/ru keys match", () => {
    expect(leafKeys(ruChat).sort()).toEqual(leafKeys(enChat).sort());
  });

  it("crm en/ru keys match", () => {
    expect(leafKeys(ruCrm).sort()).toEqual(leafKeys(enCrm).sort());
  });

  it("money en/ru keys match", () => {
    expect(leafKeys(ruMoney).sort()).toEqual(leafKeys(enMoney).sort());
  });

  it("reports en/ru keys match", () => {
    expect(leafKeys(ruReports).sort()).toEqual(leafKeys(enReports).sort());
  });

  it("feed en/ru keys match", () => {
    expect(leafKeys(ruFeed).sort()).toEqual(leafKeys(enFeed).sort());
  });

  it("settings en/ru keys match", () => {
    expect(leafKeys(ruSettings).sort()).toEqual(leafKeys(enSettings).sort());
  });

  it("rbac en/ru keys match", () => {
    expect(leafKeys(ruRbac).sort()).toEqual(leafKeys(enRbac).sort());
  });

  it("marketing en/ru keys match", () => {
    expect(leafKeys(ruMarketing).sort()).toEqual(leafKeys(enMarketing).sort());
  });

  it("patient en/ru keys match", () => {
    expect(leafKeys(ruPatient).sort()).toEqual(leafKeys(enPatient).sort());
  });

  it("founder en/ru keys match", () => {
    expect(leafKeys(ruFounder).sort()).toEqual(leafKeys(enFounder).sort());
  });
});

describe("dayjs module-scope clock", () => {
  it("CompactMonthPicker import does not set global dayjs locale to ru", async () => {
    dayjs.locale("en");
    await import("@/shared/ui/CompactMonthPicker");
    expect(dayjs.locale()).toBe("en");
  }, 15_000);

  it("AdminStaffCalendarPage import does not set global dayjs locale to ru", async () => {
    dayjs.locale("en");
    await import("@/admin/pages/AdminStaffCalendarPage");
    expect(dayjs.locale()).toBe("en");
  }, 15_000);
});
