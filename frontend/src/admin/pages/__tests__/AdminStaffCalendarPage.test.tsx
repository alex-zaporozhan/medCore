import { describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { renderWithI18n } from "@/i18n/testUtils";
import AdminStaffCalendarPage, {
  filterTimeDraft,
  formatTimeDraft,
  isReadyTimedRange,
  isValidHhmm,
  normalizeTimeBlur,
  resolvePickerClock,
  shiftHhmm,
} from "../AdminStaffCalendarPage";

vi.mock("@/hooks", () => ({
  useAdminSession: () => ({
    data: {
      permissions: ["manage_staff_collab", "invite_staff_calendar_participants", "view_tasks"],
    },
    isLoading: false,
  }),
  useAdminAdmins: () => ({ data: [], isLoading: false }),
  useStaffCalendarMonthGrid: () => ({
    data: {
      days: [],
      month: { from: "2026-08-01", to: "2026-08-31" },
      notification_signals: { unseen_invites_count: 0, reminders_due_now_count: 0 },
    },
    isLoading: false,
    isError: false,
    error: null,
  }),
  useCreateStaffCalendarEvent: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateStaffCalendarEvent: () => ({ mutate: vi.fn(), isPending: false }),
  useAckStaffCalendarInvitation: () => ({ mutate: vi.fn(), isPending: false }),
  useStaffCalendarEventDetails: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

vi.mock("@/hooks/useAdminTaskDetails", () => ({
  useAdminTaskDetails: () => ({ data: undefined, isLoading: false }),
}));

vi.mock("@/hooks/useAdminTasks", () => ({
  useAdminTasksList: () => ({ data: [] }),
  useAdminTasksMyFocus: () => ({ data: [] }),
  useAdminTasksOpen: () => ({ data: [] }),
}));

vi.mock("@/api/client", () => ({
  getAdminId: () => "admin-1",
}));

async function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderWithI18n(
    <QueryClientProvider client={client}>
      <MantineProvider>
        <MemoryRouter>
          <AdminStaffCalendarPage />
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>,
    { locale: "en" },
  );
}

describe("filterTimeDraft / formatTimeDraft / normalizeTimeBlur", () => {
  it("does not live-pad three digits", () => {
    expect(filterTimeDraft("930")).toBe("930");
    expect(filterTimeDraft("09:30")).toBe("09:30");
    expect(filterTimeDraft("ab9c3")).toBe("93");
    expect(formatTimeDraft("930")).toBe("930");
  });

  it("inserts a colon after a valid hour and keeps it while typing minutes", () => {
    expect(formatTimeDraft("09")).toBe("09:");
    expect(formatTimeDraft("09:3", "09:")).toBe("09:3");
    expect(formatTimeDraft("09:30", "09:3")).toBe("09:30");
    expect(formatTimeDraft("0900")).toBe("09:00");
  });

  it("does not bounce the colon back when deleting it", () => {
    expect(formatTimeDraft("09", "09:")).toBe("09");
  });

  it("normalizes 1–4 digits on blur", () => {
    expect(normalizeTimeBlur("9")).toBe("09:00");
    expect(normalizeTimeBlur("09")).toBe("09:00");
    expect(normalizeTimeBlur("09:")).toBe("09:00");
    expect(normalizeTimeBlur("930")).toBe("09:30");
    expect(normalizeTimeBlur("0930")).toBe("09:30");
    expect(normalizeTimeBlur("0999")).toBe("09:59");
    expect(normalizeTimeBlur("")).toBe("");
  });
});

describe("isValidHhmm / resolvePickerClock", () => {
  it("accepts only complete 00–23:00–59 clocks", () => {
    expect(isValidHhmm("09:30")).toBe(true);
    expect(isValidHhmm("09:")).toBe(false);
    expect(isValidHhmm("24:00")).toBe(false);
    expect(isValidHhmm("09:99")).toBe(false);
    expect(isValidHhmm("")).toBe(false);
  });

  it("does not wrap a 3-digit draft as hour % 24", () => {
    expect(resolvePickerClock("930", "10:00")).toEqual({ hour: 9, minute: 30 });
    expect(resolvePickerClock("99", "10:00")).toEqual({ hour: 10, minute: 0 });
    expect(resolvePickerClock("09:", "10:00")).toEqual({ hour: 9, minute: 0 });
  });

  it("requires end strictly after start", () => {
    expect(isReadyTimedRange("09:00", "09:00", "2026-08-24")).toBe(false);
    expect(isReadyTimedRange("09:00", "10:00", "2026-08-24")).toBe(true);
    expect(isReadyTimedRange("09:", "10:00", "2026-08-24")).toBe(false);
  });
});

describe("shiftHhmm", () => {
  it("clamps to the same day", () => {
    expect(shiftHhmm("09:30", 60)).toBe("10:30");
    expect(shiftHhmm("23:00", 60)).toBe("23:55");
    expect(shiftHhmm("00:05", -60)).toBe("00:00");
  });
});

describe("AdminStaffCalendarPage EN chrome and time inputs", () => {
  it("opens New event with EN chrome, blur pad, and no native time widgets on all-day", async () => {
    await renderPage();

    expect(screen.getByText("Calendar")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "New event" }));

    // lockScroll must stay off: otherwise body pointer-events:none blocks the admin navbar.
    expect(document.body.style.pointerEvents).not.toBe("none");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /new event/i })).toBeTruthy();
    });
    let node: HTMLElement | null = screen.getByRole("heading", { name: /new event/i });
    let inner: HTMLElement | null = null;
    while (node) {
      if (
        node.style.left.includes("--app-shell-navbar-offset") &&
        node.style.justifyContent === "center"
      ) {
        inner = node;
        break;
      }
      node = node.parentElement;
    }
    expect(inner).toBeTruthy();
    expect(inner?.style.paddingLeft).toBe("");
    expect(inner?.style.width).toBe("auto");

    expect(screen.queryByText("Участники")).toBeNull();
    expect(screen.queryByText("Подтвердили")).toBeNull();
    expect(screen.queryByText("Календарь")).toBeNull();
    expect(document.querySelector('input[type="time"]')).toBeNull();
    expect(document.querySelector('input[type="datetime-local"]')).toBeNull();

    await waitFor(() => {
      expect(document.querySelectorAll('input[placeholder="09:30"]').length).toBe(2);
    });
    const timeFields = Array.from(
      document.querySelectorAll('input[placeholder="09:30"]'),
    ) as HTMLInputElement[];
    fireEvent.change(timeFields[0], { target: { value: "930" } });
    expect((timeFields[0] as HTMLInputElement).value).toBe("930");
    fireEvent.blur(timeFields[0]);
    expect((timeFields[0] as HTMLInputElement).value).toBe("09:30");

    fireEvent.change(timeFields[1], { target: { value: "09" } });
    expect((timeFields[1] as HTMLInputElement).value).toBe("09:");
    fireEvent.blur(timeFields[1]);
    expect((timeFields[1] as HTMLInputElement).value).toBe("09:00");

    fireEvent.change(timeFields[0], { target: { value: "0900" } });
    expect((timeFields[0] as HTMLInputElement).value).toBe("09:00");

    const createBtn = screen.getByRole("button", { name: "Create" });
    expect(createBtn).toHaveProperty("disabled", true);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Standup" } });
    expect(createBtn).toHaveProperty("disabled", true);

    fireEvent.click(screen.getByRole("switch", { name: "All day" }));
    expect(screen.queryByPlaceholderText("09:30")).toBeNull();
    expect(document.querySelector('input[type="time"]')).toBeNull();
    expect(document.querySelector('input[type="datetime-local"]')).toBeNull();
  });

  it("opens the time wheel as a popover with every hour clickable", async () => {
    await renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New event" }));
    await waitFor(() => {
      expect(document.querySelectorAll('input[placeholder="09:30"]').length).toBe(2);
    });

    fireEvent.click(screen.getByLabelText("Choose start time"));
    await waitFor(() => {
      expect(document.querySelector('[data-hour="0"]')).toBeTruthy();
      expect(document.querySelector('[data-hour="23"]')).toBeTruthy();
    });
    expect(document.querySelectorAll("[data-hour]").length).toBe(24);
    expect(document.querySelectorAll("[data-minute]").length).toBe(12);
    expect(document.querySelector(".staff-cal-modal-content [data-hour]")).toBeNull();

    fireEvent.click(document.querySelector('[data-hour="9"]') as HTMLElement);
    const timeFields = Array.from(
      document.querySelectorAll('input[placeholder="09:30"]'),
    ) as HTMLInputElement[];
    expect(timeFields[0].value).toBe("09:00");
    expect(timeFields[1].value).toBe("10:00");
    expect(screen.getByText("Hours")).toBeTruthy();
    expect(screen.getByText("Minutes")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Standup" } });
    expect(screen.getByRole("button", { name: "Create" })).toHaveProperty("disabled", false);
  });
});
