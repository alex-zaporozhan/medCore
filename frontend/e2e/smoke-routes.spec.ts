import { test, expect } from "@playwright/test";

/**
 * Уровень B-0: публичные маршруты без API и без логина — проверка, что shell отдаётся.
 * Полный уровень B (сессия админа/пациента) — расширять осознанно; см. docker-compose profile e2e и scripts в package.json.
 */
test.describe("route shells (no auth)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("ui.locale", "en");
    });
  });

  test("landing", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /The operating system for growing your business/i })).toBeVisible();
  });

  test("clinic sign-in at /admin/login", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page).toHaveURL(/\/admin\/login/);
    await expect(page.getByRole("heading", { name: /clinic staff sign-in/i })).toBeVisible();
  });

  test("public /login shows patient and clinic entry", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: /^Sign in$/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Clinic: staff and owner/i })).toBeVisible();
  });

  test("marketing /pricing redirects to signup (unified checkout)", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page).toHaveURL(/\/signup$/);
    await expect(page.getByRole("heading", { name: /Register your organization/i })).toBeVisible();
  });

  test("marketing sandbox shell", async ({ page }) => {
    await page.goto("/sandbox");
    await expect(page.getByRole("heading", { name: /The demo environment is being prepared/i })).toBeVisible();
  });

  test("marketing signup shell (PII consent gate)", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: /Register your organization/i })).toBeVisible();
    await expect(page.getByText(/I agree to processing of the owner/i)).toBeVisible();
    await expect(page.getByText(/Choose a plan and pay/i)).toBeVisible();
  });

  test("owner invite accept shell", async ({ page }) => {
    await page.goto("/signup/owner-invite");
    await expect(page.getByRole("heading", { name: /Owner invitation/i })).toBeVisible();
  });

  test("platform founder login page", async ({ page }) => {
    await page.goto("/platform/login");
    await expect(page).toHaveURL(/\/platform\/login/);
    await expect(page.getByRole("heading", { name: /platform founder/i })).toBeVisible();
  });

  test("platform area redirects to /platform/login without founder JWT", async ({ page }) => {
    await page.goto("/platform/dashboard");
    await expect(page).toHaveURL(/\/platform\/login/);
  });

  test("platform provision-queue redirects without founder JWT (Phase 2 reconcile shell)", async ({
    page,
  }) => {
    await page.goto("/platform/provision-queue");
    await expect(page).toHaveURL(/\/platform\/login/);
  });

  test("platform enterprise leads redirects without founder JWT", async ({ page }) => {
    await page.goto("/platform/leads");
    await expect(page).toHaveURL(/\/platform\/login/);
  });
});
