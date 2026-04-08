import { describe, expect, it } from "vitest";
import {
  AdminClinicProvider,
  PatientAuthProvider,
  useAdminClinic,
  useBusinessLexicon,
  usePatientAuth,
} from "@/contexts";
import {
  useAiAgent,
  useClinics,
  useCrmLeads,
  isRevenueHunterEnabled,
} from "@/hooks";
import {
  ErrorBoundary,
  formatQueryError,
  getBookingErrorMessage,
  EmptyState,
  QueryErrorAlert,
  QueryListStates,
} from "@/shared";

/**
 * Smoke: единые баррели `hooks/`, `contexts/`, `shared/`.
 * Не проверяет рантайм-хуки вне провайдеров — только наличие публичного API.
 */
describe("frontend structure (phase 4 barrels)", () => {
  it("exports separated admin and patient contexts", () => {
    expect(typeof PatientAuthProvider).toBe("function");
    expect(typeof AdminClinicProvider).toBe("function");
    expect(typeof usePatientAuth).toBe("function");
    expect(typeof useAdminClinic).toBe("function");
    expect(typeof useBusinessLexicon).toBe("function");
  });

  it("exports domain hooks barrel", () => {
    expect(typeof useClinics).toBe("function");
    expect(typeof useAiAgent).toBe("function");
    expect(typeof useCrmLeads).toBe("function");
    expect(typeof isRevenueHunterEnabled).toBe("function");
  });

  it("exports shared UI and helpers without domain pages", () => {
    expect(typeof ErrorBoundary).toBe("function");
    expect(typeof getBookingErrorMessage).toBe("function");
    expect(typeof formatQueryError).toBe("function");
    expect(typeof EmptyState).toBe("function");
    expect(typeof QueryErrorAlert).toBe("function");
    expect(typeof QueryListStates).toBe("function");
  });
});
