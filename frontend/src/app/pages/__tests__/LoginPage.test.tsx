import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils";
import PatientSignInPage from "@/auth/PatientSignInPage";

const mockVerify = vi.fn();

vi.mock("@/contexts/PatientAuthContext", () => ({
  usePatientAuth: () => ({ login: vi.fn() }),
}));

vi.mock("@/contexts/PatientEntryContext", () => ({
  usePatientEntry: () => ({ clinicSlug: "demo-clinic" }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAgreement: () => ({ data: { allow_registration_without_mailing_consent: true } }),
  useSendCode: () => ({
    mutate: (_phone: string, opts: { onSuccess?: () => void }) => opts?.onSuccess?.(),
    isPending: false,
    error: null,
  }),
  useVerifyCode: () => ({
    mutate: mockVerify,
    isPending: false,
    error: null,
  }),
}));

vi.mock("@/shared/utmTracking", () => ({
  getCurrentUtm: () => ({
    session_id: "sess-123",
    utm_source: "google",
    utm_medium: "cpc",
    utm_campaign: "camp",
    utm_content: "ad",
    utm_term: "kw",
    landing_page: "/?utm_source=google",
    anchor: "#hero",
  }),
}));

describe("Patient sign-in UTM integration", () => {
  beforeEach(() => {
    mockVerify.mockReset();
  });

  it("passes UTM context from getCurrentUtm to verifyCode.mutate payload", () => {
    renderWithProviders(<PatientSignInPage />, {
      withRouter: true,
      routerInitialEntries: ["/c/demo-clinic/sign-in"],
    });

    const phoneInput = screen.getByLabelText("Телефон");
    fireEvent.change(phoneInput, { target: { value: "9001234567" } });

    const getCodeButton = screen.getByText("Получить код");
    fireEvent.click(getCodeButton);

    const codeInput = screen.getByLabelText("Код из SMS");
    fireEvent.change(codeInput, { target: { value: "1234" } });

    const loginButton = screen.getByText("Войти");
    fireEvent.click(loginButton);

    expect(mockVerify).toHaveBeenCalledTimes(1);
    const [payload] = mockVerify.mock.calls[0];
    expect(payload.session_id).toBe("sess-123");
    expect(payload.utm_source).toBe("google");
    expect(payload.utm_medium).toBe("cpc");
    expect(payload.utm_campaign).toBe("camp");
    expect(payload.utm_content).toBe("ad");
    expect(payload.utm_term).toBe("kw");
    expect(payload.landing_page).toBe("/?utm_source=google");
    expect(payload.anchor).toBe("#hero");
  });
});
