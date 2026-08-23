import { test, expect } from "@playwright/test";

/**
 * Статический smoke: маршрут `/c/:clinicSlug/sign-in` без бэкенда (Vite preview).
 * Соответствует LEAD: пациентский вход только в контексте клиники.
 */
test.describe("patient entry by clinic slug", () => {
  test("scoped sign-in shows patient-only shell", async ({ page }) => {
    await page.goto("/c/demo-clinic/sign-in");
    await expect(page.getByRole("heading", { name: /Patient sign-in/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Sign in to your account/i })).toBeVisible();
    await expect(page.getByText(/Clinic patient account/i)).toBeVisible();
  });

  test("invalid /c/sign-in (no clinic slug) redirects to public login with hint", async ({ page }) => {
    await page.goto("/c/sign-in");
    await expect(page).toHaveURL(/\/login.*patientEntry=patient-url-needs-clinic-slug/);
    await expect(page.getByText(/three path segments/i)).toBeVisible();
  });

  test("short /c/:slug redirects to sign-in", async ({ page }) => {
    await page.goto("/c/demo-clinic");
    await expect(page).toHaveURL(/\/c\/demo-clinic\/sign-in$/);
    await expect(page.getByRole("heading", { name: /Patient sign-in/i })).toBeVisible();
  });
});
