import { afterEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { doctorRoleLabel } from "@/shared/doctorRoleI18n";

describe("doctorRoleLabel", () => {
  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("uses directory.doctorDrawer.roles for a known specialist_role", () => {
    expect(doctorRoleLabel({ specialist_role: "doctor" })).toBe("Doctor");
    expect(doctorRoleLabel({ specialist_role: "nurse" })).toBe("Nurse");
  });

  it("returns custom name for specialist_role other", () => {
    expect(
      doctorRoleLabel({
        specialist_role: "other",
        specialist_role_custom_name: "Orthodontist",
      }),
    ).toBe("Orthodontist");
  });

  it("does not use display_role and falls back to schedule.specialist", () => {
    expect(
      doctorRoleLabel({
        specialist_role: "not_a_role",
        display_role: "Врач",
      }),
    ).toBe("Specialist");
  });

  it("maps API nurse/therapist codes onto directory keys", () => {
    expect(doctorRoleLabel({ specialist_role: "nurse" })).toBe("Nurse");
    expect(doctorRoleLabel({ specialist_role: "therapist" })).toBe("Therapist");
  });
});
