import { test, expect } from "@playwright/test";

/**
 * Статический smoke: маршрут `/c/:clinicSlug/sign-in` без бэкенда (Vite preview).
 * Соответствует LEAD: пациентский вход только в контексте клиники.
 */
test.describe("patient entry by clinic slug", () => {
  test("scoped sign-in shows patient-only shell", async ({ page }) => {
    await page.goto("/c/demo-clinic/sign-in");
    await expect(page.getByRole("heading", { name: /Вход пациента/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Вход в личный кабинет/i })).toBeVisible();
    await expect(page.getByText(/Личный кабинет клиники/i)).toBeVisible();
  });

  test("invalid /c/sign-in (no clinic slug) redirects to landing with hint", async ({ page }) => {
    await page.goto("/c/sign-in");
    await expect(page).toHaveURL(/patientEntry=patient-url-needs-clinic-slug/);
    await expect(page.getByText(/три части пути/i)).toBeVisible();
  });

  test("short /c/:slug redirects to sign-in", async ({ page }) => {
    await page.goto("/c/demo-clinic");
    await expect(page).toHaveURL(/\/c\/demo-clinic\/sign-in$/);
    await expect(page.getByRole("heading", { name: /Вход пациента/i })).toBeVisible();
  });
});
