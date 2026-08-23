import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { afterEach, describe, expect, it } from "vitest";
import i18n, { UI_LOCALE_STORAGE_KEY } from "../index";
import { PUBLIC_HTML_LANG, isDocumentLocalePath, useUiLocale } from "../useUiLocale";

function wrapper({ children }: { children: ReactNode }) {
  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}

describe("isDocumentLocalePath", () => {
  it("follows ui.locale on staff/public/founder chrome and /admin*", () => {
    expect(isDocumentLocalePath("/admin")).toBe(true);
    expect(isDocumentLocalePath("/admin/login")).toBe(true);
    expect(isDocumentLocalePath("/login")).toBe(true);
    expect(isDocumentLocalePath("/login/")).toBe(true);
    expect(isDocumentLocalePath("/platform/login")).toBe(true);
    expect(isDocumentLocalePath("/platform/login/mfa")).toBe(true);
    expect(isDocumentLocalePath("/platform/dashboard")).toBe(true);
    expect(isDocumentLocalePath("/")).toBe(true);
    expect(isDocumentLocalePath("/signup")).toBe(true);
    expect(isDocumentLocalePath("/signup/owner-invite")).toBe(true);
    expect(isDocumentLocalePath("/pricing")).toBe(true);
    expect(isDocumentLocalePath("/app/chat")).toBe(true);
    expect(isDocumentLocalePath("/c/demo-clinic/sign-in")).toBe(true);
    expect(isDocumentLocalePath("/sandbox")).toBe(true);
    expect(isDocumentLocalePath("/legal/privacy")).toBe(true);
    expect(isDocumentLocalePath("/legal/terms")).toBe(true);
    expect(isDocumentLocalePath("/demo-clinic/doctors/ivanov")).toBe(true);
  });
});

describe("useUiLocale", () => {
  afterEach(async () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    await i18n.changeLanguage("en");
    window.history.replaceState({}, "", "/app/chat");
    document.documentElement.lang = PUBLIC_HTML_LANG;
  });

  it("setLocale persists ui.locale", async () => {
    const { result } = renderHook(() => useUiLocale(), { wrapper });
    await act(async () => {
      result.current.setLocale("ru");
    });
    expect(localStorage.getItem(UI_LOCALE_STORAGE_KEY)).toBe("ru");
    await waitFor(() => {
      expect(result.current.locale).toBe("ru");
    });
  });

  it("sets documentElement.lang on /admin* and on landing /; patient /app follows ui.locale", async () => {
    window.history.replaceState({}, "", "/admin/login");
    const { result } = renderHook(() => useUiLocale(), { wrapper });
    await act(async () => {
      result.current.setLocale("en");
    });
    expect(document.documentElement.lang).toBe("en");

    await waitFor(() => {
      expect(document.documentElement.lang).toBe("en");
    });
    expect(document.title).toMatch(/MedCore/);

    window.history.pushState({}, "", "/app/chat");
    await waitFor(() => {
      expect(document.documentElement.lang).toBe("en");
    });

    window.history.pushState({}, "", "/admin/login");
    await waitFor(() => {
      expect(document.documentElement.lang).toBe("en");
    });
  });

  it("sets documentElement.lang from ui.locale on /login and /platform/login", async () => {
    window.history.replaceState({}, "", "/login");
    const { result } = renderHook(() => useUiLocale(), { wrapper });
    await act(async () => {
      result.current.setLocale("en");
    });
    await waitFor(() => {
      expect(document.documentElement.lang).toBe("en");
    });

    window.history.pushState({}, "", "/platform/login");
    await waitFor(() => {
      expect(document.documentElement.lang).toBe("en");
    });
  });

  it("storage event from another tab changes language", async () => {
    window.history.replaceState({}, "", "/admin/login");
    const { result } = renderHook(() => useUiLocale(), { wrapper });
    await act(async () => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: UI_LOCALE_STORAGE_KEY, newValue: "ru" }),
      );
    });
    await waitFor(() => {
      expect(result.current.locale).toBe("ru");
    });
    expect(document.documentElement.lang).toBe("ru");
  });
});
