import { test, expect } from "@playwright/test";

/**
 * Уровень B-0: публичные маршруты без API и без логина — проверка, что shell отдаётся.
 * Полный уровень B (сессия админа/пациента) — расширять осознанно; см. docker-compose profile e2e и scripts в package.json.
 */
test.describe("route shells (no auth)", () => {
  test("landing", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Dental Booking Business OS/i })).toBeVisible();
  });

  test("clinic sign-in at /admin/login", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page).toHaveURL(/\/admin\/login/);
    await expect(page.getByRole("heading", { name: /Вход в Business OS/i })).toBeVisible();
  });

  test("legacy /login redirects to landing with patient hint", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveURL(/\/\?patientEntry=need-clinic/);
  });

  test("marketing pricing shell (FE-E1)", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByRole("heading", { name: /Тарифы для клиник/i })).toBeVisible();
  });

  test("marketing signup shell (PII consent gate)", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: /Регистрация клиники/i })).toBeVisible();
    await expect(page.getByText(/Согласен\(на\) на обработку персональных данных/i)).toBeVisible();
  });

  test("platform founder login page", async ({ page }) => {
    await page.goto("/platform/login");
    await expect(page).toHaveURL(/\/platform\/login/);
    await expect(page.getByRole("heading", { name: /Основатель платформы/i })).toBeVisible();
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
});
