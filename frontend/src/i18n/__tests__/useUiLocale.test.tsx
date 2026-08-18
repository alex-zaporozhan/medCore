import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { afterEach, describe, expect, it } from "vitest";
import i18n, { UI_LOCALE_STORAGE_KEY } from "../index";
import { PUBLIC_HTML_LANG, useUiLocale } from "../useUiLocale";

function wrapper({ children }: { children: ReactNode }) {
  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}

describe("useUiLocale", () => {
  afterEach(async () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    await i18n.changeLanguage("en");
    window.history.replaceState({}, "", "/");
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

  it("sets documentElement.lang on /admin* and restores public lang elsewhere", async () => {
    window.history.replaceState({}, "", "/admin/login");
    const { result } = renderHook(() => useUiLocale(), { wrapper });
    await act(async () => {
      result.current.setLocale("en");
    });
    expect(document.documentElement.lang).toBe("en");

    window.history.pushState({}, "", "/");
    await waitFor(() => {
      expect(document.documentElement.lang).toBe(PUBLIC_HTML_LANG);
    });

    window.history.pushState({}, "", "/admin/login");
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
