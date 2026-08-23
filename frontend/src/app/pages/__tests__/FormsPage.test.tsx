import { vi, describe, it, expect, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils";
import FormsPage from "../FormsPage";

vi.mock("@/contexts/PatientAuthContext", () => ({
  usePatientAuth: () => ({ accessToken: "test-token" }),
}));

vi.mock("@/hooks", () => ({
  usePatientPendingForms: () => ({
    data: [
      {
        id: "t1",
        clinic_id: "c1",
        code: "health_questionnaire",
        name: "Анкета здоровья",
        description: null,
        version: 1,
        schema: {
          fields: [
            {
              id: "full_name",
              label: "ФИО",
              type: "text",
              required: true,
              sensitive: true,
            },
          ],
        },
        requires_signature: false,
        active: true,
      },
    ],
    isLoading: false,
    isError: false,
    error: null,
  }),
  useSubmitPatientForm: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

describe("FormsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders list of pending forms and allows opening a form", () => {
    renderWithProviders(<FormsPage />);

    expect(screen.getByText("Forms and consents")).toBeInTheDocument();
    const card = screen.getByText("Анкета здоровья");
    fireEvent.click(card);
    expect(screen.getByText("ФИО")).toBeInTheDocument();
  });
});

