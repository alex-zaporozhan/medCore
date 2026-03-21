import { describe, expect, it } from "vitest";
import { parseAdminJwtClinicId } from "../client";

describe("parseAdminJwtClinicId", () => {
  it("extracts clinic_id from JWT payload (base64)", () => {
    const payload = btoa(JSON.stringify({ clinic_id: "550e8400-e29b-41d4-a716-446655440000", type: "admin" }));
    const token = `header.${payload}.sig`;
    expect(parseAdminJwtClinicId(token)).toBe("550e8400-e29b-41d4-a716-446655440000");
  });

  it("returns null for invalid token", () => {
    expect(parseAdminJwtClinicId(null)).toBeNull();
    expect(parseAdminJwtClinicId("not-a-jwt")).toBeNull();
  });
});
