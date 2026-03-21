import { test, expect } from "@playwright/test";

/**
 * Уровень B-0: публичные маршруты без API и без логина — проверка, что shell отдаётся.
 * Полный уровень B (сессия админа/пациента) — см. `docs/artifacts/ARCH_FRONTEND_VISUAL_UNIFICATION_AND_E2E_ROADMAP.md`.
 */
test.describe("route shells (no auth)", () => {
  test("landing", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Dental Booking Business OS/i })).toBeVisible();
  });

  test("admin login page", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page.getByRole("heading", { name: /Вход в админку/i })).toBeVisible();
  });

  test("patient login page", async ({ page }) => {
    await page.goto("/login");
    await expect(
      page.getByRole("heading", { name: /Вход в личный кабинет|Регистрация в клинике/i }),
    ).toBeVisible();
  });
});
