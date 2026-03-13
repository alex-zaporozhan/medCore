import type { Booking, DailySchedule, ScheduleSlot } from "@/api/types";
import { Box, Table, Text } from "@mantine/core";
import {
  DndContext,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  useDraggable,
  type DragEndEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

/** patient_id -> display name (ФИО или телефон) */
interface ScheduleCalendarProps {
  schedule: DailySchedule;
  bookings: Booking[] | undefined;
  onBookingClick: (booking: Booking) => void;
  onReschedule: (payload: { bookingId: string; time: string }) => void;
  onEmptySlotClick?: (payload: { time: string }) => void;
  patientNameMap?: Record<string, string>;
}

interface SlotWithBooking extends ScheduleSlot {
  booking?: Booking;
}

function findBookingForSlot(
  slot: ScheduleSlot,
  date: string,
  bookings: Booking[] | undefined,
): Booking | undefined {
  if (!bookings || bookings.length === 0) {
    return undefined;
  }

  if (slot.booking_id) {
    const byId = bookings.find((b) => b.id === slot.booking_id);
    if (byId) {
      return byId;
    }
  }

  const byTime = bookings.find(
    (b) =>
      b.appointment_date === date &&
      String(b.appointment_time).slice(0, 5) === slot.start_time.slice(0, 5),
  );

  return byTime;
}

function DroppableRow({
  slot,
  booking,
  date,
  children,
}: {
  slot: SlotWithBooking;
  booking?: Booking;
  date: string;
  children: React.ReactNode;
}) {
  const timeKey = slot.start_time.slice(0, 5);
  const id = `slot-${date}-${timeKey}`;
  const { isOver, setNodeRef } = useDroppable({
    id,
  });

  const background =
    isOver && slot.is_available ? "var(--primary-light, rgba(59,130,246,0.12))" : undefined;

  return (
    <Table.Tr
      ref={setNodeRef}
      className={!slot.is_available ? "schedule-row-busy" : undefined}
      style={{
        cursor: booking ? "grab" : "default",
        background,
      }}
      data-slot-id={id}
      data-slot-time={timeKey}
    >
      {children}
    </Table.Tr>
  );
}

function DraggableBooking({
  booking,
  children,
}: {
  booking: Booking;
  children: React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: booking.id,
  });

  const style = {
    transform: transform ? CSS.Translate.toString(transform) : undefined,
  };

  return (
    <Box ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {children}
    </Box>
  );
}

export function ScheduleCalendar({
  schedule,
  bookings,
  onBookingClick,
  onReschedule,
  onEmptySlotClick,
  patientNameMap,
}: ScheduleCalendarProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 4 },
    }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over) {
      return;
    }

    const bookingId = String(active.id);

    // Найти целевой слот по droppable-id
    const targetSlot = schedule.slots.find(
      (s) =>
        `slot-${schedule.date}-${s.start_time.slice(0, 5)}` ===
        String(over.id),
    );

    if (!targetSlot) {
      return;
    }

    // Разрешаем перенос только в доступные слоты
    if (!targetSlot.is_available) {
      return;
    }

    const targetTime = targetSlot.start_time.slice(0, 5);

    // Найти саму запись, чтобы сравнить с исходным временем
    const booking = bookings?.find((b) => b.id === bookingId);
    if (!booking) {
      return;
    }

    const currentTime = String(booking.appointment_time).slice(0, 5);

    // Если слот тот же самый — ничего не делаем
    if (currentTime === targetTime) {
      return;
    }

    onReschedule({ bookingId, time: targetTime });
  };

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <Box className="schedule-grid-card">
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Время</Table.Th>
              <Table.Th>Статус</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {schedule.slots.map((slot) => {
              const booking = findBookingForSlot(slot, schedule.date, bookings);

              return (
                <DroppableRow
                  key={`${schedule.date}-${slot.start_time}`}
                  slot={slot}
                  booking={booking}
                  date={schedule.date}
                >
                  <Table.Td>
                    {slot.start_time} – {slot.end_time}
                  </Table.Td>
                  <Table.Td>
                    {booking ? (
                      <DraggableBooking booking={booking}>
                        <Box
                          onClick={() => onBookingClick(booking)}
                          style={{
                            background: "var(--bg-card)",
                            borderRadius: 8,
                            padding: "4px 8px",
                            border: "1px solid var(--divider)",
                          }}
                        >
                          <Text size="sm" fw={500}>
                            Занято
                          </Text>
                          <Text size="xs" c="dimmed">
                            Пациент: {patientNameMap?.[booking.patient_id] ?? booking.patient_id}
                          </Text>
                        </Box>
                      </DraggableBooking>
                    ) : (
                      <Box
                        style={{ cursor: onEmptySlotClick ? "pointer" : "default" }}
                        onClick={() =>
                          onEmptySlotClick?.({
                            time: slot.start_time.slice(0, 5),
                          })
                        }
                      >
                        <Text size="sm" c="dimmed">
                          Свободен
                        </Text>
                      </Box>
                    )}
                  </Table.Td>
                </DroppableRow>
              );
            })}
          </Table.Tbody>
        </Table>
      </Box>
    </DndContext>
  );
}

