import type { ReactElement, ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import i18n, { UI_LOCALE_STORAGE_KEY } from "@/i18n";
import { renderWithI18n } from "@/i18n/testUtils";
import ClinicSignInPage from "../ClinicSignInPage";
import { SignInShell } from "../SignInShell";

function wrap(ui: ReactNode): ReactElement {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("ClinicSignInPage A1", () => {
  afterEach(async () => {
    localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
    await i18n.changeLanguage("en");
  });

  it("renders EN heading and locale switch on the form column", async () => {
    await renderWithI18n(wrap(<ClinicSignInPage />), { locale: "en" });
    expect(screen.getByRole("heading", { name: "Clinic staff sign-in" })).toBeTruthy();
    expect(screen.getByLabelText("Language")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: /Вход для сотрудников клиники/i })).toBeNull();
  });

  it("renders RU heading when locale is ru", async () => {
    await renderWithI18n(wrap(<ClinicSignInPage />), { locale: "ru" });
    expect(screen.getByRole("heading", { name: "Вход для сотрудников клиники" })).toBeTruthy();
  });

  it("locale switch persists ui.locale and retitles the page", async () => {
    await renderWithI18n(wrap(<ClinicSignInPage />), { locale: "en" });
    fireEvent.click(screen.getByText("RU"));
    expect(localStorage.getItem(UI_LOCALE_STORAGE_KEY)).toBe("ru");
    expect(screen.getByRole("heading", { name: "Вход для сотрудников клиники" })).toBeTruthy();
  });

  it("password min error follows locale after switch", async () => {
    await renderWithI18n(wrap(<ClinicSignInPage />), { locale: "en" });
    fireEvent.change(screen.getByPlaceholderText("admin@example.com"), {
      target: { value: "staff@clinic.example" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByText("Password must be at least 8 characters")).toBeTruthy();
    fireEvent.click(screen.getByText("RU"));
    expect(screen.getByText("Пароль должен быть не менее 8 символов")).toBeTruthy();
  });
});

describe("SignInShell patient variant", () => {
  it("does not mount the locale switch", async () => {
    await renderWithI18n(
      wrap(<SignInShell variant="patient">form</SignInShell>),
      { locale: "en" },
    );
    expect(screen.queryByLabelText("Language")).toBeNull();
    expect(screen.getByText("form")).toBeTruthy();
  });
});
