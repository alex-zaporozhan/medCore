import type { ReactElement, ReactNode } from "react";
import { act, render, type RenderOptions, type RenderResult } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import i18n, { normalizeUiLocale, type UiLocale } from "./index";

export type RenderWithI18nOptions = Omit<RenderOptions, "wrapper"> & {
  locale?: UiLocale;
};

export async function renderWithI18n(
  ui: ReactElement,
  options?: RenderWithI18nOptions,
): Promise<RenderResult> {
  const { locale = "en", ...renderOptions } = options ?? {};
  try {
    if (normalizeUiLocale(i18n.resolvedLanguage ?? i18n.language) !== locale) {
      await i18n.changeLanguage(locale);
    }
  } catch (err: unknown) {
    console.error("renderWithI18n changeLanguage failed", { locale, err });
    throw err;
  }
  function Wrapper({ children }: { children: ReactNode }) {
    return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
  }
  let view: RenderResult | undefined;
  await act(async () => {
    view = render(ui, { wrapper: Wrapper, ...renderOptions });
  });
  return view as RenderResult;
}
