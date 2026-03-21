import type { ReactElement } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MantineProvider } from "@mantine/core";
import { appTheme } from "@/theme";
import AdminSalesPipelinePage from "../AdminSalesPipelinePage";

vi.mock("react-router-dom", () => ({
  useSearchParams: () => [new URLSearchParams()],
}));

vi.mock("@/contexts/AdminClinicContext", () => ({
  useAdminClinic: () => ({
    clinics: [],
    currentClinicId: "clinic-1",
    setCurrentClinicId: vi.fn(),
    isLoading: false,
    error: null,
    businessLexicon: null,
  }),
}));

vi.mock("@/shared/aiFeatures", () => ({
  useAiFeatures: () => ({
    get: (id: string) => ({ id, label: id, status: "beta" }),
  }),
  getAiFeatureBadgeColor: () => "blue",
  getAiFeatureStatusText: () => "beta",
  getAiFeatureTooltip: () => "beta",
}));

vi.mock("@/shared/uiEvents", () => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/hooks/useAvailableAiTools", () => ({
  useAvailableAiTools: () => ({
    hasAll: () => true,
  }),
}));

vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: (opts: { count: number }) => ({
    getVirtualItems: () =>
      Array.from({ length: opts.count }, (_, i) => ({
        index: i,
        start: i * 148,
        key: String(i),
        size: 148,
      })),
    getTotalSize: () => opts.count * 148,
    measureElement: vi.fn(),
  }),
}));

const testQueryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithMantine(ui: ReactElement) {
  return render(
    <QueryClientProvider client={testQueryClient}>
      <MantineProvider theme={appTheme} defaultColorScheme="light">
        {ui}
      </MantineProvider>
    </QueryClientProvider>
  );
}

const mockPipelines = [
  {
    id: "pipe-1",
    clinic_id: "clinic-1",
    name: "Основная воронка",
    description: null,
    is_default: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockStages = [
  {
    id: "stage-new",
    clinic_id: "clinic-1",
    pipeline_id: "pipe-1",
    order: 0,
    code: "new",
    name: "Новое",
    probability: 10,
    color: "#888",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "stage-booked",
    clinic_id: "clinic-1",
    pipeline_id: "pipe-1",
    order: 1,
    code: "booked",
    name: "Записан",
    probability: 50,
    color: "#38a",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockLeads = [
  {
    id: "lead-1",
    clinic_id: "clinic-1",
    pipeline_id: "pipe-1",
    stage_id: "stage-new",
    omnichannel_contact_id: null,
    patient_id: null,
    primary_booking_id: null,
    visit_attribution_id: null,
    title: "Лид из чата",
    source: "omnichannel",
    utm_source: null,
    utm_medium: null,
    utm_campaign: null,
    utm_content: null,
    utm_term: null,
    estimated_value: "5000",
    actual_value: "0",
    status: "open",
    created_at: "2026-03-01T10:00:00Z",
    updated_at: "2026-03-01T10:00:00Z",
    closed_at: null,
    lost_reason: null,
  },
];

const mockLeadDetails = {
  lead: mockLeads[0],
  notes: [
    {
      id: "note-1",
      clinic_id: "clinic-1",
      lead_id: "lead-1",
      author_admin_id: "admin-1",
      text: "Перезвонить завтра",
      created_at: "2026-03-01T12:00:00Z",
    },
  ],
};

const mockUseCrmPipelines = vi.fn();
const mockUseCrmStages = vi.fn();
const mockUseCrmKanbanStageLeadsInfinite = vi.fn();
const mockUseCrmLeadDetails = vi.fn();
const mockUseCreateLeadNote = vi.fn();

vi.mock("@/hooks/useCrmLeads", () => ({
  useCrmPipelines: () => mockUseCrmPipelines(),
  useCrmStages: (pipelineId: string | null) => mockUseCrmStages(pipelineId),
  useCrmKanbanStageLeadsInfinite: (filters: { stageId: string }) =>
    mockUseCrmKanbanStageLeadsInfinite(filters),
  useCrmLeadDetails: (leadId: string | null) => mockUseCrmLeadDetails(leadId),
  useCreateLeadNote: () => mockUseCreateLeadNote(),
  useAiLeadSummary: () => ({
    data: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
  useAiSuggestNextStage: () => ({
    data: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
  useAiUpdateLeadStage: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useAiCreateTaskForLead: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useAiIgnoreLeadRecommendation: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  usePipelineStageSemantics: () => ({
    data: {
      pipeline_id: "pipe-1",
      supported_semantics: ["start", "scheduled", "won"],
      mappings: [],
      resolved_stage_semantics: [
        { stage_id: "stage-new", semantic: "start" },
        { stage_id: "stage-booked", semantic: "scheduled" },
      ],
    },
    isLoading: false,
  }),
  useUpdateLeadStage: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

describe("AdminSalesPipelinePage Kanban", () => {
  beforeEach(() => {
    mockUseCrmPipelines.mockReturnValue({
      data: mockPipelines,
      isLoading: false,
    });
    mockUseCrmStages.mockImplementation(() => ({
      data: mockStages,
      isLoading: false,
    }));
    mockUseCrmKanbanStageLeadsInfinite.mockImplementation(({ stageId }: { stageId: string }) => ({
      data: {
        pages: [
          {
            items: mockLeads.filter((l) => l.stage_id === stageId),
            total: 1,
            next_cursor: null,
          },
        ],
        pageParams: [undefined],
      },
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
    }));
    mockUseCrmLeadDetails.mockReturnValue({
      data: null,
      isLoading: false,
    });
    mockUseCreateLeadNote.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  it("renders page title and filter controls", () => {
    renderWithMantine(<AdminSalesPipelinePage />);

    expect(screen.getByText("CRM‑воронка продаж")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Pipeline" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Стадия" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Статус" })).toBeInTheDocument();
    expect(screen.getByLabelText("Поиск")).toBeInTheDocument();
  });

  it("renders Kanban columns from stages when pipeline and stages are loaded", () => {
    renderWithMantine(<AdminSalesPipelinePage />);

    expect(screen.getAllByText("Новое").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Записан").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/\(1\)\s+—/)).toBeInTheDocument();
  });

  it("renders lead cards with title, source, estimated and actual value, status", () => {
    renderWithMantine(<AdminSalesPipelinePage />);

    expect(screen.getByText("Лид из чата")).toBeInTheDocument();
    expect(screen.getByText(/Источник: omnichannel/)).toBeInTheDocument();
    expect(screen.getByText(/Оценка: 5000/)).toBeInTheDocument();
    expect(screen.getByText(/Факт: 0/)).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
  });

  it("shows empty state in right panel when no lead selected", () => {
    renderWithMantine(<AdminSalesPipelinePage />);

    expect(screen.getByText("Выберите лид")).toBeInTheDocument();
    expect(
      screen.getByText(/Кликните по карточке лида в Kanban‑доске/)
    ).toBeInTheDocument();
  });

  it("shows lead details and notes when a lead card is clicked", () => {
    mockUseCrmLeadDetails.mockImplementation((leadId: string | null) => ({
      data: leadId === "lead-1" ? mockLeadDetails : null,
      isLoading: false,
    }));

    renderWithMantine(<AdminSalesPipelinePage />);

    const leadCard = screen.getByText("Лид из чата");
    fireEvent.click(leadCard);

    expect(screen.getByText("Перезвонить завтра")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Добавить заметку...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Сохранить заметку/ })).toBeInTheDocument();
  });
});
