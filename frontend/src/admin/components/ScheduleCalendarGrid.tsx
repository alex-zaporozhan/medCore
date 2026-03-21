import type { Booking, DoctorSlot } from "@/api/types";
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

export interface ScheduleCalendarGridProps {
  doctors: { id: string; name: string }[];
  date: string;
  times: string[];
  byDoctor: Record<string, DoctorSlot[]>;
  bookings: Booking[] | undefined;
  /** patient_id -> display name (e.g. full_name or phone) */
  patientNameMap?: Record<string, string>;
  /** service_id -> display name */
  serviceNameMap?: Record<string, string>;
  onBookingClick: (booking: Booking) => void;
  onReschedule: (payload: {
    bookingId: string;
    toDoctorId: string;
    date: string;
    time: string;
  }) => void;
  onEmptySlotClick?: (payload: { doctorId: string; time: string }) => void;
}

function timeStr(t: string): string {
  return String(t).slice(0, 5);
}

function findBooking(
  slot: DoctorSlot,
  doctorId: string,
  date: string,
  bookings: Booking[] | undefined
): Booking | undefined {
  if (!slot.booking_id || !bookings?.length) return undefined;
  const b = bookings.find(
    (x) =>
      x.id === slot.booking_id ||
      (x.doctor_id === doctorId &&
        x.appointment_date === date &&
        timeStr(x.appointment_time) === timeStr(slot.start_time))
  );
  return b;
}

function DroppableCell({
  doctorId,
  time,
  slot,
  booking,
  date,
  children,
  onEmptyClick,
}: {
  doctorId: string;
  time: string;
  slot: DoctorSlot;
  booking?: Booking;
  date: string;
  children: React.ReactNode;
  onEmptyClick?: () => void;
}) {
  const id = `cell-${doctorId}__${date}__${time}`;
  const { isOver, setNodeRef } = useDroppable({ id });
  const canDrop = slot.is_available;
  return (
    <Table.Td
      ref={setNodeRef}
      style={{
        background: isOver && canDrop ? "var(--primary-light, rgba(59,130,246,0.12))" : undefined,
        cursor: booking ? "grab" : onEmptyClick ? "pointer" : "default",
        minWidth: 100,
      }}
      data-droppable-id={id}
      data-doctor-id={doctorId}
      data-time={time}
      onClick={!booking && onEmptyClick ? onEmptyClick : undefined}
    >
      {children}
    </Table.Td>
  );
}

function DraggableBookingCard({
  booking,
  children,
}: {
  booking: Booking;
  children: React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: booking.id,
  });
  const style = transform ? { transform: CSS.Translate.toString(transform) } : undefined;
  return (
    <Box ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {children}
    </Box>
  );
}

export function ScheduleCalendarGrid({
  doctors,
  date,
  times,
  byDoctor,
  bookings,
  patientNameMap,
  serviceNameMap,
  onBookingClick,
  onReschedule,
  onEmptySlotClick,
}: ScheduleCalendarGridProps) {
  const getPatientLabel = (patientId: string) =>
    patientNameMap?.[patientId] ?? patientId;
  const getServiceLabel = (serviceId: string) =>
    serviceNameMap?.[serviceId] ?? serviceId;
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const overId = String(over.id);
    if (!overId.startsWith("cell-")) return;
    const rest = overId.replace("cell-", "");
    const [toDoctorId, , time] = rest.split("__");
    if (!time || !toDoctorId) return;
    const bookingId = String(active.id);
    const booking = bookings?.find((b) => b.id === bookingId);
    if (!booking) return;
    const currentTime = timeStr(booking.appointment_time);
    if (booking.doctor_id === toDoctorId && currentTime === time) return;
    onReschedule({ bookingId, toDoctorId, date, time });
  };

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <Box className="schedule-grid-card">
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Время</Table.Th>
              {doctors.map((d) => (
                <Table.Th key={d.id}>{d.name}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {times.map((t) => {
              const timeKey = timeStr(t);
              return (
                <Table.Tr key={timeKey}>
                  <Table.Td>
                    <Text size="sm">{timeKey}</Text>
                  </Table.Td>
                  {doctors.map((doc) => {
                    const slots = byDoctor[doc.id];
                    const slot = slots?.find((s) => timeStr(s.start_time) === timeKey);
                    const booking = slot
                      ? findBooking(slot, doc.id, date, bookings)
                      : undefined;
                    return (
                      <DroppableCell
                        key={doc.id}
                        doctorId={doc.id}
                        time={timeKey}
                        slot={
                          slot ?? {
                            start_time: t,
                            end_time: t,
                            is_available: false,
                            booking_id: null,
                            status: null,
                          }
                        }
                        booking={booking}
                        date={date}
                        onEmptyClick={
                          onEmptySlotClick && slot?.is_available
                            ? () => onEmptySlotClick({ doctorId: doc.id, time: timeKey })
                            : undefined
                        }
                      >
                        {booking ? (
                          <DraggableBookingCard booking={booking}>
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
                                {getPatientLabel(booking.patient_id)}
                              </Text>
                              <Text size="xs" c="dimmed">
                                {getServiceLabel(booking.service_id)}
                              </Text>
                            </Box>
                          </DraggableBookingCard>
                        ) : (
                          <Text size="sm" c="dimmed">
                            {slot?.is_available ? "Свободен" : "—"}
                          </Text>
                        )}
                      </DroppableCell>
                    );
                  })}
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Box>
    </DndContext>
  );
}
