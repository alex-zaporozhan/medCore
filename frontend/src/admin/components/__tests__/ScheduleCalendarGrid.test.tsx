import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import type { Booking, DoctorSlot } from "@/api/types";
import {
  findBooking,
  isScheduleCellOpenForCreate,
  ScheduleCalendarGrid,
} from "../ScheduleCalendarGrid";
import { renderWithI18n } from "@/i18n/testUtils";

async function wrapGrid(ui: ReactNode) {
  return renderWithI18n(
    <MantineProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>,
    { locale: "en" },
  );
}

const slotFree: DoctorSlot = {
  start_time: "10:00:00",
  end_time: "10:30:00",
  is_available: true,
  booking_id: null,
  status: null,
};

const slotBlocked: DoctorSlot = {
  ...slotFree,
  is_available: false,
};

const booking: Booking = {
  id: "b-1",
  clinic_id: "c-1",
  patient_id: "p-1",
  doctor_id: "d-1",
  service_id: "s-1",
  appointment_date: "2026-08-17",
  appointment_time: "10:00:00",
  status: "pending",
  prepayment_amount: "0",
  payment_id: null,
  notes: null,
  patient_name: "Иванов Иван",
};

describe("findBooking", () => {
  it("matches by doctor and time when slot.booking_id is missing", () => {
    const found = findBooking(slotFree, "d-1", "2026-08-17", [booking]);
    expect(found?.id).toBe("b-1");
  });

  it("returns undefined when the cell is empty", () => {
    expect(findBooking(slotFree, "d-1", "2026-08-17", [])).toBeUndefined();
  });
});

describe("isScheduleCellOpenForCreate", () => {
  it("is open when there is no booking", () => {
    expect(isScheduleCellOpenForCreate(undefined)).toBe(true);
  });

  it("is closed when a booking occupies the cell", () => {
    expect(isScheduleCellOpenForCreate(booking)).toBe(false);
  });
});

describe("ScheduleCalendarGrid empty-cell click", () => {
  it("opens create when the slot is listed as unavailable but empty", async () => {
    const onEmpty = vi.fn();
    await wrapGrid(
      <ScheduleCalendarGrid
        doctors={[{ id: "d-1", name: "Dr A" }]}
        date="2026-08-17"
        times={["10:00"]}
        byDoctor={{ "d-1": [slotBlocked] }}
        bookings={[]}
        onBookingClick={vi.fn()}
        onReschedule={vi.fn()}
        onEmptySlotClick={onEmpty}
      />,
    );
    fireEvent.click(screen.getByText("Free"));
    expect(onEmpty).toHaveBeenCalledWith({ doctorId: "d-1", time: "10:00" });
  });

  it("opens create when the time row has no slot object", async () => {
    const onEmpty = vi.fn();
    await wrapGrid(
      <ScheduleCalendarGrid
        doctors={[{ id: "d-1", name: "Dr A" }]}
        date="2026-08-17"
        times={["11:00"]}
        byDoctor={{ "d-1": [] }}
        bookings={[]}
        onBookingClick={vi.fn()}
        onReschedule={vi.fn()}
        onEmptySlotClick={onEmpty}
      />,
    );
    fireEvent.click(screen.getByText("Free"));
    expect(onEmpty).toHaveBeenCalledWith({ doctorId: "d-1", time: "11:00" });
  });

  it("does not open create on an occupied cell", async () => {
    const onEmpty = vi.fn();
    await wrapGrid(
      <ScheduleCalendarGrid
        doctors={[{ id: "d-1", name: "Dr A" }]}
        date="2026-08-17"
        times={["10:00"]}
        byDoctor={{ "d-1": [{ ...slotFree, booking_id: booking.id }] }}
        bookings={[booking]}
        onBookingClick={vi.fn()}
        onReschedule={vi.fn()}
        onEmptySlotClick={onEmpty}
      />,
    );
    fireEvent.click(screen.getByText("Иванов Иван"));
    expect(onEmpty).not.toHaveBeenCalled();
  });

  it("shows awaiting payment badge, not Busy, for awaiting_payment", async () => {
    await wrapGrid(
      <ScheduleCalendarGrid
        doctors={[{ id: "d-1", name: "Dr A" }]}
        date="2026-08-17"
        times={["10:00"]}
        byDoctor={{ "d-1": [{ ...slotFree, booking_id: booking.id }] }}
        bookings={[{ ...booking, status: "awaiting_payment" }]}
        onBookingClick={vi.fn()}
        onReschedule={vi.fn()}
        onEmptySlotClick={vi.fn()}
      />,
    );
    expect(screen.getByText("Awaiting payment")).toBeTruthy();
    expect(screen.queryByText("Busy")).toBeNull();
  });
});
