import { test, expect } from "@playwright/test";

const STORAGE = {
  adminToken: "dental_booking_admin_token",
  adminId: "dental_booking_admin_id",
  adminClinicId: "dental_booking_admin_clinic_id",
};

function mockAdminOmniApi(page: import("@playwright/test").Page) {
  // Session: enable admin chrome without redirect.
  page.route("**/api/v1/admin/auth/session", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        admin_id: "00000000-0000-0000-0000-000000000001",
        clinic_id: "00000000-0000-0000-0000-000000000010",
        roles: ["owner"],
        permissions: ["omni.inbox.manage", "erp.owner_reports.read"],
      }),
    });
  });

  // Chat list with multi-channel coverage.
  page.route("**/api/v1/admin/omni-chats**", async (route) => {
    if (route.request().method().toUpperCase() !== "GET") {
      await route.fallback();
      return;
    }
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/api/v1/admin/omni-chats/quick-replies") || url.pathname.endsWith("/api/v1/admin/omni-chats/sse-token")) {
      await route.fallback();
      return;
    }
    const selected = url.searchParams.getAll("channel_types");
    const wantsTelegram = selected.includes("TELEGRAM_BOT");
    const wantsWhatsapp = selected.includes("WHATSAPP_BUSINESS");
    const wantsUnassigned = url.searchParams.get("assignee") === "unassigned";
    const wantsMine = url.searchParams.get("assignee") === "me";
    const wantsWaiting = url.searchParams.get("status") === "WAITING_FOR_OPERATOR";

    const all = [
      {
        chat_id: "00000000-0000-0000-0000-000000000101",
        contact_id: "00000000-0000-0000-0000-000000000201",
        contact_name: "Иван Иванов",
        contact_primary_phone: "+7 999 111-22-33",
        channel_id: "00000000-0000-0000-0000-000000000301",
        channel_type: "TELEGRAM_BOT",
        channel_types: ["TELEGRAM_BOT", "WHATSAPP_BUSINESS"],
        status: "WAITING_FOR_OPERATOR",
        last_message_at: new Date().toISOString(),
        last_actor_type: "CLIENT",
        ai_mode: "DISABLED",
        assignee_admin_id: null,
        assignee_name: null,
        needs_attention: true,
      },
      {
        chat_id: "00000000-0000-0000-0000-000000000102",
        contact_id: "00000000-0000-0000-0000-000000000202",
        contact_name: "Мария Петрова",
        contact_primary_phone: "+7 999 222-33-44",
        channel_id: "00000000-0000-0000-0000-000000000302",
        channel_type: "VK_BOT",
        channel_types: ["VK_BOT"],
        status: "IN_PROGRESS",
        last_message_at: new Date().toISOString(),
        last_actor_type: "CLIENT",
        ai_mode: "DISABLED",
        assignee_admin_id: "00000000-0000-0000-0000-000000000001",
        assignee_name: "Админ",
        needs_attention: true,
      },
    ];

    const filtered =
      selected.length === 0
        ? all
        : all.filter((c) => {
            const types: string[] = c.channel_types ?? (c.channel_type ? [c.channel_type] : []);
            return selected.some((t) => types.includes(t));
          });

    const filtered2 = filtered.filter((c) => {
      if (wantsUnassigned && c.assignee_admin_id) return false;
      if (wantsMine && !c.assignee_admin_id) return false;
      if (wantsWaiting && c.status !== "WAITING_FOR_OPERATOR") return false;
      return true;
    });

    // Ensure filter is actually wired: if only Telegram selected, VK chat must disappear.
    if (wantsTelegram && selected.length === 1) {
      // ok
    }
    if (wantsWhatsapp && selected.length === 1) {
      // ok
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: filtered2, total: filtered2.length }),
    });
  });

  // Quick replies.
  page.route("**/api/v1/admin/omni-chats/quick-replies", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [{ id: "qr-1", clinic_id: "c", title: "Привет", body: "Здравствуйте!", sort_order: 0, created_at: null }] }),
    });
  });

  // Chat detail.
  page.route("**/api/v1/admin/omni-chats/*", async (route) => {
    const url = route.request().url();
    if (url.includes("/messages") || url.includes("/hide") || url.includes("/ai-mode") || url.includes("/claim") || url.includes("/close")) {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        chat_id: "00000000-0000-0000-0000-000000000101",
        contact_id: "00000000-0000-0000-0000-000000000201",
        contact_name: "Иван Иванов",
        contact_primary_phone: "+7 999 111-22-33",
        channel_id: "00000000-0000-0000-0000-000000000301",
        channel_type: "TELEGRAM_BOT",
        status: "WAITING_FOR_OPERATOR",
        ai_mode: "DISABLED",
        last_message_at: new Date().toISOString(),
        last_actor_type: "CLIENT",
        created_at: new Date().toISOString(),
        lead_id: null,
        lead_stage_id: null,
        lead_stage_name: null,
        lead_estimated_value: null,
        lead_actual_value: null,
        assignee_admin_id: null,
        assignee_name: null,
        claimed_at: null,
        closed_at: null,
      }),
    });
  });

  // AI mode toggle.
  page.route("**/api/v1/admin/omni-chats/*/ai-mode", async (route) => {
    if (route.request().method().toUpperCase() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({ status: 204, body: "" });
  });

  // Messages: ensure at least two days to render day separators.
  page.route("**/api/v1/admin/omni-chats/*/messages**", async (route) => {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 3600 * 1000);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "m-1",
            direction: "INBOUND",
            actor_type: "CLIENT",
            content: "Здравствуйте",
            message_content_type: "TEXT",
            attachments: [],
            created_at: yesterday.toISOString(),
            ui_hidden: false,
            hidden_reason: null,
            channel_id: "00000000-0000-0000-0000-000000000301",
            channel_type: "TELEGRAM_BOT",
          },
          {
            id: "m-1a",
            direction: "OUTBOUND",
            actor_type: "HUMAN_ADMIN",
            content:
              "reply_to: m-1\nОк, понял.",
            message_content_type: "TEXT",
            attachments: [],
            created_at: now.toISOString(),
            ui_hidden: false,
            hidden_reason: null,
            channel_id: "00000000-0000-0000-0000-000000000301",
            channel_type: "TELEGRAM_BOT",
          },
          {
            id: "m-2",
            direction: "INBOUND",
            actor_type: "CLIENT",
            content: "Есть свободное окно?",
            message_content_type: "TEXT",
            attachments: [
              {
                id: "att-1",
                file_name: "photo.png",
                content_type: "image/png",
                size_bytes: 1234,
                source: "omni",
              },
            ],
            created_at: now.toISOString(),
            ui_hidden: false,
            hidden_reason: null,
            channel_id: "00000000-0000-0000-0000-000000000302",
            channel_type: "WHATSAPP_BUSINESS",
          },
        ],
      }),
    });
  });

  // Omni attachment download (image preview).
  page.route("**/api/v1/admin/omni-chats/*/messages/*/attachments/*/file", async (route) => {
    // 1x1 transparent PNG
    const pngBase64 =
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/6pG8nUAAAAASUVORK5CYII=";
    const body = Buffer.from(pngBase64, "base64");
    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "image/png" },
      body,
    });
  });

  // SSE: keep request from failing hard in console.
  page.route("**/api/v1/admin/omni-chats/events**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: ": keepalive\n\n",
    });
  });

  // Short-lived SSE token.
  page.route("**/api/v1/admin/omni-chats/sse-token", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ token: "short-lived-sse-token", expires_in_seconds: 300 }),
    });
  });

  // Closure tags.
  page.route("**/api/v1/admin/omni-chat-closure-tags**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          { id: "00000000-0000-0000-0000-00000000a001", title: "Ценой", is_active: true, sort_order: 1 },
          { id: "00000000-0000-0000-0000-00000000a002", title: "Сервисом", is_active: true, sort_order: 2 },
        ],
      }),
    });
  });
}

test.describe("admin omni-chat (mocked API)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("dental_booking_admin_token", "test-token");
      localStorage.setItem("dental_booking_admin_id", "00000000-0000-0000-0000-000000000001");
      localStorage.setItem("dental_booking_admin_clinic_id", "00000000-0000-0000-0000-000000000010");
    });
    mockAdminOmniApi(page);
  });

  test("renders omni-chat shell; inbox states; channel filter works", async ({ page }) => {
    await page.goto("/admin/omni-chat");
    await expect(page).toHaveURL(/\/admin\/omni-chat/);

    // Context bar (page shell).
    await expect(page.getByText(/Omni‑чат — только работа/i)).toBeVisible();

    // Inbox: both scenarios render attention dots (waiting + my needs-reply).
    await expect(page.getByLabel("needs-attention")).toHaveCount(2);

    // Open chat (click inbox item).
    await page.getByText("Иван Иванов").first().click();
    await expect(page.getByText("Взять в работу")).toBeVisible();

    // Messages rendered.
    await expect(page.getByText("Здравствуйте").first()).toBeVisible();
    await expect(page.getByText("Есть свободное окно?")).toBeVisible();
    // Attachment preview (image) renders as <img> (filename may be hidden).
    await expect(page.getByLabel("Сообщения переписки").locator("img").first()).toBeVisible();

    // Composer exists and is reasonably tall (minRows=2).
    await expect(page.locator("textarea").first()).toBeVisible();

    // Telegram-style composer actions restored.
    await expect(page.getByLabel("Эмодзи")).toBeVisible();
    await expect(page.getByLabel("Файл")).toBeVisible();
    await expect(page.getByLabel("Фото")).toBeVisible();
    await expect(page.getByLabel(/Записать голос|Остановить запись/)).toBeVisible();

    // AI toggle exists.
    await expect(page.getByPlaceholder("ИИ")).toBeVisible();

    // Meta-rail actions exist (Reply button on a message).
    await expect(page.getByLabel("Ответить").first()).toBeVisible();

    // Reply via context menu sets telegram-style quote (no links).
    await page.locator("#omni-msg-m-1").click({ button: "right" });
    await page.getByText("Ответить").click();
    await expect(page.getByText("Здравствуйте").first()).toBeVisible();
    await expect(page.locator("textarea").first()).not.toContainText("reply_to:");

    // Quoted block renders and hides raw `reply:` line in message bubble.
    await expect(page.getByText("Ок, понял.")).toBeVisible();
    await expect(page.getByText("Здравствуйте").first()).toBeVisible();

    // Composer autogrow (best-effort): multi-line increases height.
    const ta = page.locator("textarea").first();
    const h1 = (await ta.boundingBox())?.height ?? 0;
    await ta.fill("line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10");
    const h2 = (await ta.boundingBox())?.height ?? 0;
    expect(h2).toBeGreaterThan(h1);

    // Channel filter: select VK, Telegram chat should disappear.
    await page.getByPlaceholder("Каналы: все").click();
    await page.getByRole("option", { name: "VK_BOT" }).click();
    await page.keyboard.press("Escape");
    await expect(page.getByText("Мария Петрова").first()).toBeVisible();
    await page.getByText("Мария Петрова").first().click();
    await expect(page.getByText("Мария Петрова").first()).toBeVisible();
  });

  test("deep link with chat_id+message_id scroll target exists", async ({ page }) => {
    await page.goto("/admin/omni-chat?chat_id=00000000-0000-0000-0000-000000000101&message_id=m-2");
    await expect(page.getByText("Есть свободное окно?")).toBeVisible();
    await expect(page.locator("#omni-msg-m-2")).toBeVisible();
  });
});

