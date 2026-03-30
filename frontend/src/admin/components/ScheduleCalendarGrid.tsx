import type { Booking, DoctorSlot } from "@/api/types";
import type { CSSProperties } from "react";
import { Anchor, Badge, Box, Group, Table, Text } from "@mantine/core";
import { IconMessageCircle } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
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

const ROW_H = 80;
const TIME_COL_W = 80;

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

function looksLikeUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s.trim());
}

/** Монолитная сетка: Swiss calendar tokens (`index.css` --calendar-*). Единый каркас — DESIGN_SCHEDULE_MODAL_SEMANTICS_85_PLUS §1. */
function bookingSlotSurface(status: string): CSSProperties {
  const s = status.toLowerCase();
  const base: CSSProperties = {
    borderRadius: "var(--calendar-slot-radius)",
    border: "1px solid var(--calendar-card-border)",
    boxShadow: "var(--calendar-card-shadow)",
    borderLeftWidth: "var(--calendar-bar-width)",
    borderLeftStyle: "solid",
  };
  if (s === "completed") {
    return {
      ...base,
      background: "var(--calendar-completed-bg)",
      borderLeftColor: "var(--calendar-completed-bar)",
    };
  }
  if (s === "in_progress") {
    return {
      ...base,
      background: "var(--calendar-in-progress-bg)",
      borderLeftColor: "var(--calendar-in-progress-bar)",
    };
  }
  if (s === "cancelled" || s === "no_show") {
    return {
      ...base,
      background: "var(--calendar-negative-bg)",
      borderLeftColor: "var(--calendar-negative-bar)",
    };
  }
  if (s === "pending") {
    return {
      ...base,
      background: "var(--calendar-scheduled-bg)",
      borderLeftColor: "var(--calendar-scheduled-bar)",
    };
  }
  if (s === "registered") {
    return {
      ...base,
      background: "var(--calendar-scheduled-bg)",
      borderLeftColor: "var(--calendar-attention-denim-bar)",
    };
  }
  if (s === "confirmed") {
    return {
      ...base,
      background: "var(--calendar-attention-denim-bg)",
      borderLeftColor: "var(--calendar-attention-denim-bar)",
    };
  }
  return {
    ...base,
    background: "var(--calendar-scheduled-bg)",
    borderLeftColor: "var(--calendar-scheduled-bar)",
  };
}

function textColorsForStatus(status: string): { primary: string; secondary: string } {
  const s = status.toLowerCase();
  if (s === "completed")
    return { primary: "var(--calendar-completed-title)", secondary: "var(--calendar-completed-meta)" };
  if (s === "in_progress")
    return { primary: "var(--calendar-in-progress-title)", secondary: "var(--calendar-in-progress-meta)" };
  if (s === "cancelled" || s === "no_show")
    return { primary: "var(--calendar-negative-title)", secondary: "var(--calendar-negative-meta)" };
  if (s === "pending")
    return { primary: "var(--calendar-scheduled-title)", secondary: "var(--calendar-scheduled-meta)" };
  if (s === "registered")
    return { primary: "var(--calendar-scheduled-title)", secondary: "var(--calendar-scheduled-meta)" };
  if (s === "confirmed")
    return { primary: "var(--calendar-attention-denim-title)", secondary: "var(--calendar-attention-denim-meta)" };
  return { primary: "var(--calendar-scheduled-title)", secondary: "var(--calendar-scheduled-meta)" };
}

type CalendarBadgeConfig = { label: string; styles: { root: CSSProperties } };

function statusBadge(status: string): CalendarBadgeConfig {
  const s = status.toLowerCase();
  if (s === "completed") {
    return {
      label: "Завершён",
      styles: {
        root: {
          backgroundColor: "var(--calendar-completed-badge-bg)",
          color: "var(--calendar-completed-badge-text)",
        },
      },
    };
  }
  if (s === "in_progress") {
    return {
      label: "На приёме",
      styles: {
        root: {
          backgroundColor: "var(--calendar-in-progress-badge-bg)",
          color: "var(--calendar-in-progress-badge-text)",
          border: "1px solid var(--calendar-in-progress-badge-border)",
        },
      },
    };
  }
  if (s === "cancelled") {
    return {
      label: "Отмена",
      styles: {
        root: {
          backgroundColor: "var(--calendar-negative-badge-bg)",
          color: "var(--calendar-negative-badge-text)",
        },
      },
    };
  }
  if (s === "no_show") {
    return {
      label: "Неявка",
      styles: {
        root: {
          backgroundColor: "var(--calendar-negative-badge-bg)",
          color: "var(--calendar-negative-badge-text)",
        },
      },
    };
  }
  if (s === "pending") {
    return {
      label: "Ожидает",
      styles: {
        root: {
          backgroundColor: "var(--calendar-scheduled-badge-bg)",
          color: "var(--calendar-scheduled-badge-text)",
        },
      },
    };
  }
  if (s === "registered") {
    return {
      label: "Зарегистрирован",
      styles: {
        root: {
          backgroundColor: "var(--calendar-scheduled-badge-bg)",
          color: "var(--calendar-attention-denim-badge-text)",
          border: "1px solid var(--calendar-attention-denim-badge-bg)",
        },
      },
    };
  }
  if (s === "confirmed") {
    return {
      label: "Подтверждён",
      styles: {
        root: {
          backgroundColor: "var(--calendar-attention-denim-badge-bg)",
          color: "var(--calendar-attention-denim-badge-text)",
        },
      },
    };
  }
  return {
    label: "Занято",
    styles: {
      root: {
        backgroundColor: "var(--calendar-scheduled-badge-bg)",
        color: "var(--calendar-scheduled-badge-text)",
      },
    },
  };
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
        height: ROW_H,
        verticalAlign: "top",
        padding: 2,
        background: isOver && canDrop ? "var(--mantine-color-gray-1)" : undefined,
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
    <Box ref={setNodeRef} style={{ ...style, height: "100%", minHeight: 0 }} {...attributes} {...listeners}>
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
  const getPatientLabel = (booking: Booking) => {
    const raw =
      (booking.patient_name && booking.patient_name.trim()) ||
      patientNameMap?.[booking.patient_id] ||
      booking.patient_id;
    if (typeof raw === "string" && looksLikeUuid(raw)) return "Имя неизвестно";
    return raw;
  };
  const getServiceLabel = (serviceId: string) => {
    const name = serviceNameMap?.[serviceId] ?? serviceId;
    if (looksLikeUuid(String(name))) return "Услуга";
    return name;
  };
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
        <Table striped={false} withTableBorder withColumnBorders withRowBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th
                style={{
                  width: TIME_COL_W,
                  maxWidth: TIME_COL_W,
                }}
              >
                <Text size="xs" c="dimmed" fw={500} ta="right" pr={4}>
                  Время
                </Text>
              </Table.Th>
              {doctors.map((d) => (
                <Table.Th key={d.id}>
                  <Anchor
                    component={Link}
                    to={`${ROUTE_PATHS.admin.doctors}?doctor_id=${d.id}&doctor_tab=schedule`}
                    size="sm"
                    fw={600}
                    c="gray.8"
                    underline="hover"
                    lineClamp={2}
                    style={{ lineHeight: 1.3 }}
                  >
                    {d.name}
                  </Anchor>
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {times.map((t) => {
              const timeKey = timeStr(t);
              return (
                <Table.Tr key={timeKey}>
                  <Table.Td
                    style={{
                      width: TIME_COL_W,
                      maxWidth: TIME_COL_W,
                      height: ROW_H,
                      verticalAlign: "top",
                      padding: "8px 6px",
                    }}
                  >
                    <Text size="sm" c="dimmed" fw={500} ta="right">
                      {timeKey}
                    </Text>
                  </Table.Td>
                  {doctors.map((doc) => {
                    const slots = byDoctor[doc.id];
                    const slot = slots?.find((s) => timeStr(s.start_time) === timeKey);
                    const booking = slot
                      ? findBooking(slot, doc.id, date, bookings)
                      : undefined;
                    const sb = booking ? statusBadge(booking.status) : null;
                    const tc = booking ? textColorsForStatus(booking.status) : undefined;
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
                                ...bookingSlotSurface(booking.status),
                                width: "100%",
                                height: "100%",
                                minHeight: ROW_H - 4,
                                boxSizing: "border-box",
                                padding: "6px 8px",
                                display: "flex",
                                flexDirection: "column",
                                justifyContent: "flex-start",
                                overflow: "hidden",
                              }}
                            >
                              {sb && (
                                <Badge size="xs" variant="transparent" styles={sb.styles} mb={4}>
                                  {sb.label}
                                </Badge>
                              )}
                              <Group gap={6} wrap="nowrap" align="center">
                                <Anchor
                                  component={Link}
                                  to={`${ROUTE_PATHS.admin.patients}?patient_id=${booking.patient_id}`}
                                  size="sm"
                                  fw={600}
                                  lineClamp={1}
                                  underline="hover"
                                  style={{
                                    flex: 1,
                                    minWidth: 0,
                                    color: tc?.primary,
                                  }}
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {getPatientLabel(booking)}
                                </Anchor>
                                {booking.notes?.trim() ? (
                                  <IconMessageCircle
                                    size={14}
                                    stroke={1.5}
                                    color="var(--text-muted)"
                                    aria-label="Есть комментарий к записи"
                                  />
                                ) : null}
                              </Group>
                              <Text size="xs" fw={500} lineClamp={1} style={{ color: tc?.secondary }}>
                                {getServiceLabel(booking.service_id)}
                              </Text>
                            </Box>
                          </DraggableBookingCard>
                        ) : (
                          <Text size="sm" c="dimmed" p={4}>
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
