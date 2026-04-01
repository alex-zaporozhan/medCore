import { describe, expect, it, vi } from "vitest";

vi.mock("@/api/client", () => {
  return {
    API_BASE: "/api",
    api: {
      post: vi.fn(async () => ({ token: "t123", expires_in_seconds: 120 })),
    },
  };
});

import { fetchAdminPatientMedicalFileDownloadUrl } from "@/hooks/useAdminPatientMedical";
import { api } from "@/api/client";

describe("fetchAdminPatientMedicalFileDownloadUrl (enterprise stream)", () => {
  it("issues token and returns stream url", async () => {
    const url = await fetchAdminPatientMedicalFileDownloadUrl({
      clinicId: "c1",
      patientId: "p1",
      fileId: "f1",
    });
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(url).toContain("/api/v1/admin/clinics/c1/patients/p1/medical/files/f1:stream?token=");
    expect(url).toContain("t123");
  });
});

