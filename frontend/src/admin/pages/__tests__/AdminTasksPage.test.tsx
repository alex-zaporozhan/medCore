import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import AdminTasksPage from "../AdminTasksPage";
import { appTheme } from "@/theme";

const mutateStatus = vi.fn();
const mutateReorder = vi.fn();
const mutateBulk = vi.fn();
const mutateMeta = vi.fn();
const mutateClaim = vi.fn();
const mutateCreate = vi.fn();
const mutateComment = vi.fn();
const mutateInvite = vi.fn();
let capturedOnDragEnd: ((event: any) => void) | null = null;

const mockAdmins = [
  { id: "admin-1", full_name: "Owner Admin", email: "owner@test.local" },
  { id: "admin-2", full_name: "Doctor Admin", email: "doctor@test.local" },
];

const STATUS_ORDER_MOCK = [
  "open",
  "in_progress",
  "on_hold",
  "review",
  "done",
  "cancelled",
] as const;

const mockStreams = [
  {
    id: "stream-general",
    clinic_id: "clinic-1",
    name: "Общее",
    slug: "general",
    sort_order: 0,
    is_archived: false,
    theme: { page_tint: "none" as const },
  },
];

const mockTags: { id: string; clinic_id: string; name: string; color: string | null }[] = [];

const mockBoards = [
  {
    id: "board-default",
    clinic_id: "clinic-1",
    name: "Основная",
    kind: "clinic_wide",
    owner_admin_id: null,
    columns: STATUS_ORDER_MOCK.map((s, i) => ({
      id: `col-${s}`,
      sort_order: i + 1,
      mapped_status: s,
      label: null,
    })),
  },
];

const mockTasks = [
  {
    id: "task-1",
    clinic_id: "clinic-1",
    stream_id: "stream-general",
    tag_ids: [] as string[],
    title: "Overdue task",
    description: null,
    status: "open",
    priority: "medium",
    assignee_id: "admin-1",
    assignee_ids: ["admin-1"],
    role_assignee: null,
    due_at: "2025-01-01T10:00:00Z",
    source: "manual",
    rank: 1,
    blocked: false,
    checklist_done: false,
    stage_entered_at: "2025-01-01T10:00:00Z",
  },
  {
    id: "task-2",
    clinic_id: "clinic-1",
    stream_id: "stream-general",
    tag_ids: [] as string[],
    title: "Second open task",
    description: null,
    status: "open",
    priority: "medium",
    assignee_id: "admin-2",
    assignee_ids: ["admin-2"],
    role_assignee: null,
    due_at: "2030-01-01T10:00:00Z",
    source: "manual",
    rank: 2,
    blocked: false,
    checklist_done: true,
    stage_entered_at: "2030-01-01T10:00:00Z",
  },
  {
    id: "task-3",
    clinic_id: "clinic-1",
    stream_id: "stream-general",
    tag_ids: [] as string[],
    title: "Review task",
    description: null,
    status: "review",
    priority: "high",
    assignee_id: "admin-1",
    assignee_ids: ["admin-1"],
    role_assignee: null,
    due_at: "2030-01-01T12:00:00Z",
    source: "ai_suggested",
    rank: 1,
    blocked: false,
    checklist_done: true,
    stage_entered_at: "2030-01-01T10:00:00Z",
  },
];

vi.mock("@/api/client", () => ({
  getAdminId: () => "admin-1",
}));

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    currentClinicId: "clinic-1",
  }),
}));

vi.mock("@/hooks/usePatients", () => ({
  usePatients: () => ({
    data: [{ id: "patient-1", full_name: "Patient One", phone: "+79001112233" }],
  }),
}));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ onDragEnd, children }: any) => {
    capturedOnDragEnd = onDragEnd;
    return <div>{children}</div>;
  },
  PointerSensor: function PointerSensor() {},
  useSensor: () => ({}),
  useSensors: () => ([]),
  useDraggable: ({ id }: { id: string }) => ({
    setNodeRef: () => {},
    attributes: { "data-draggable-id": id },
    listeners: {},
    transform: null,
    isDragging: false,
  }),
  useDroppable: () => ({
    setNodeRef: () => {},
    isOver: false,
  }),
}));

vi.mock("@/hooks", () => ({
  useAdminAdmins: () => ({
    data: mockAdmins,
  }),
  useAdminTasksList: () => ({
    data: mockTasks,
    isLoading: false,
  }),
  useTaskStreamsQuery: () => ({
    data: mockStreams,
    isLoading: false,
  }),
  useTaskTagsQuery: () => ({
    data: mockTags,
    isLoading: false,
  }),
  useCreateTaskStreamMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateTaskTagMutation: () => ({ mutate: vi.fn(), isPending: false }),
  usePatchAdminTaskStreamTagsMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useAdminTasksMyFocus: () => ({ data: [] }),
  useCreateAdminTaskMutation: () => ({ mutate: mutateCreate, isPending: false }),
  useClaimAdminTaskMutation: () => ({ mutate: mutateClaim, isPending: false }),
  useUpdateAdminTaskStatusMutation: () => ({ mutate: mutateStatus, isPending: false }),
  useUpdateAdminTaskMetaMutation: () => ({ mutate: mutateMeta, isPending: false }),
  useReorderAdminTasksMutation: () => ({ mutate: mutateReorder, isPending: false }),
  useBulkUpdateAdminTaskStatusMutation: () => ({ mutate: mutateBulk, isPending: false }),
  useTaskWipPolicies: () => ({ data: { open: 8, in_progress: 6, review: 6 } }),
  useTaskTransitions: () => ({ data: [] }),
  useTaskCalendarContext: () => ({ data: [] }),
  useInviteTaskCalendarParticipants: () => ({ mutate: mutateInvite, isPending: false }),
  useTaskComments: () => ({ data: [], isLoading: false }),
  usePostTaskComment: () => ({ mutate: mutateComment, isPending: false }),
  useTaskBoardsQuery: () => ({ data: mockBoards, isLoading: false }),
  useReplaceTaskBoardColumnsMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useCreatePersonalTaskBoardMutation: () => ({ mutate: vi.fn(), isPending: false }),
  usePatchAdminTaskAssigneesMutation: () => ({ mutate: vi.fn(), isPending: false }),
  usePatchAdminTaskDueMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useAdminSession: () => ({
    data: {
      permissions: [
        "manage_tasks",
        "assign_tasks",
        "tasks.change_status",
        "tasks.manage_clinic_board",
      ],
    },
  }),
}));

const testQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, gcTime: 0, staleTime: 0 },
    mutations: { retry: false, gcTime: 0 },
  },
});

function renderPage() {
  testQueryClient.clear();
  return render(
    <MemoryRouter>
      <QueryClientProvider client={testQueryClient}>
        <MantineProvider theme={appTheme} defaultColorScheme="light">
          <AdminTasksPage />
        </MantineProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe("AdminTasksPage workstation behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOnDragEnd = null;
  });

  it("renders WIP/SLA/Aging indicators", () => {
    renderPage();
    expect(screen.getByText(/WIP 2\/8/)).toBeInTheDocument();
    expect(screen.getByText(/SLA overdue: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Aging 48h\+: 1/)).toBeInTheDocument();
  });

  it("moves task by keyboard Alt+ArrowRight", () => {
    renderPage();
    const taskCard = screen.getByText("Overdue task").closest("div");
    if (!taskCard) throw new Error("task card not found");
    fireEvent.keyDown(taskCard, { key: "ArrowRight", altKey: true });
    expect(mutateStatus).toHaveBeenCalled();
  });

  it("handles drag and drop between columns", () => {
    renderPage();
    if (!capturedOnDragEnd) throw new Error("DnD handler not captured");
    capturedOnDragEnd({
      active: { id: "task-1" },
      over: { id: "droppable-review" },
    });
    expect(mutateStatus).toHaveBeenCalledWith({ taskId: "task-1", status: "review" });
  });

  it("handles drag reorder inside a column", () => {
    renderPage();
    if (!capturedOnDragEnd) throw new Error("DnD handler not captured");
    capturedOnDragEnd({
      active: { id: "task-1" },
      over: { id: "task-slot-open--task-2" },
    });
    expect(mutateReorder).toHaveBeenCalled();
  });
});
