import { test, expect } from "@playwright/test";

const CLINIC_ID = "00000000-0000-0000-0000-000000000010";
const ADMIN_ID = "00000000-0000-0000-0000-000000000001";

/** Моки API для страницы «Лента» (дашборд) без живого backend. */
function mockAdminDashboardFeedApi(page: import("@playwright/test").Page) {
  let feedPosts: Array<Record<string, unknown>> = [];

  page.route("**/api/v1/admin/auth/session", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        clinic_id: CLINIC_ID,
        permissions: ["manage_staff_collab", "view_marketing_analytics", "view_finance"],
        roles: ["owner"],
        accessible_clinic_ids: [CLINIC_ID],
        entitlement_enforced: false,
      }),
    });
  });

  page.route("**/api/v1/clinics", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: CLINIC_ID,
          name: "Клиника E2E",
          phone: null,
          email: null,
          address: null,
          workday_start: "09:00",
          workday_end: "18:00",
          slot_duration_minutes: 30,
          prepayment_amount: "0",
        },
      ]),
    });
  });

  page.route("**/api/v1/admin/reports/dashboard-aggregate**", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        date: "2026-04-10",
        bookings_pending: 0,
        bookings_confirmed: 0,
        bookings_completed: 3,
        bookings_cancelled: 0,
        bookings_no_show: 0,
        new_patients: 1,
        chat_writers_count: 0,
        revenue: "0",
        empty_slot_hours: "2",
        day_pulse_score: 50,
      }),
    });
  });

  page.route("**/api/v1/admin/clinics/*/reports/revenue-saved-by-ai", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ amount: null }),
    });
  });

  page.route("**/api/v1/admin/staff/me/profile", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: ADMIN_ID,
        clinic_id: CLINIC_ID,
        email: "e2e@example.test",
        full_name: "Сотрудник E2E",
        birth_date: null,
        employment_status: "active",
        profession_category_id: null,
        profession_category_name: null,
      }),
    });
  });

  page.route("**/api/v1/admin/staff/feed/posts**", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(feedPosts),
      });
      return;
    }
    if (method === "POST") {
      const raw = route.request().postData();
      const parsed = raw ? (JSON.parse(raw) as { body?: string; title?: string | null }) : { body: "" };
      const newPost = {
        id: "e2e-post-1",
        title: parsed.title ?? null,
        body: parsed.body ?? "",
        author: { id: ADMIN_ID, full_name: "Сотрудник E2E" },
        created_at: new Date().toISOString(),
        comments_count: 0,
        likes_count: 0,
        liked_by_me: false,
        is_announcement: false,
        attachments: [],
      };
      feedPosts = [newPost];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(newPost),
      });
      return;
    }
    await route.fallback();
  });
}

test.describe("admin dashboard feed (mocked API)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ clinicId, adminId }) => {
        localStorage.setItem("dental_booking_admin_token", "e2e-test-token");
        localStorage.setItem("dental_booking_admin_id", adminId);
        localStorage.setItem("dental_booking_admin_clinic_id", clinicId);
      },
      { clinicId: CLINIC_ID, adminId: ADMIN_ID }
    );
    mockAdminDashboardFeedApi(page);
  });

  test("открывает модальное окно нового поста, публикует — текст появляется в ленте", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/admin\/?$/);

    await expect(page.getByText("Лента").first()).toBeVisible();

    await page.getByRole("button", { name: /Создать пост в ленте клиники/i }).click();
    const panel = page.getByRole("dialog");
    await expect(panel.getByText("Новый пост")).toBeVisible();

    const body = `E2E пост ${Date.now()}`;
    // AppleEmojiOverlayTextarea: нативный placeholder может отличаться; целимся в textarea внутри панели.
    await panel.locator("textarea").first().fill(body);
    await panel.getByRole("button", { name: "Опубликовать" }).click();

    await expect(panel.getByText("Новый пост")).not.toBeVisible();
    await expect(page.getByText(body).first()).toBeVisible();
  });
});
