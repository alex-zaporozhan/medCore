import { vi, describe, it, expect, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils";
import LoyaltyPage from "../LoyaltyPage";

vi.mock("@/contexts/PatientAuthContext", () => ({
  usePatientAuth: () => ({ accessToken: "test-token" }),
}));

vi.mock("@/hooks", () => ({
  usePatientLoyaltyMe: () => ({
    data: {
      subscriptions: [
        {
          id: "sub1",
          clinic_id: "c1",
          patient_id: "p1",
          subscription_package_id: "pkg1",
          status: "active",
          purchased_at: new Date().toISOString(),
          activated_at: new Date().toISOString(),
          expires_at: new Date().toISOString(),
          remaining_visits: 3,
          remaining_amount: null,
          payment_id: null,
          notes: null,
        },
      ],
      wallet: {
        id: "w1",
        clinic_id: "c1",
        patient_id: "p1",
        balance: "150.00",
        currency: "POINTS",
        updated_at: new Date().toISOString(),
      },
      wallet_transactions: [],
    },
    isLoading: false,
    isError: false,
    error: null,
  }),
  usePatientLoyaltyHistory: () => ({
    data: {
      items: [],
    },
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

describe("LoyaltyPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders wallet balance and active subscriptions", () => {
    renderWithProviders(<LoyaltyPage />, { withRouter: true });

    expect(screen.getByText("Мои абонементы и баллы")).toBeInTheDocument();
    expect(screen.getByText("Баланс кошелька")).toBeInTheDocument();
    expect(screen.getByText(/150.00/)).toBeInTheDocument();
    expect(screen.getByText("Digital Pass — Абонементы")).toBeInTheDocument();
    expect(screen.getByText("Записаться по абонементу")).toBeInTheDocument();
  });
});

