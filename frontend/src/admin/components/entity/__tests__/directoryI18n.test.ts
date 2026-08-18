import { describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { weekdayLabelMonFirst } from "@/admin/components/entity/DoctorEntityDrawer";
import { serviceCategoryLabel } from "@/admin/components/entity/ServiceEntityDrawer";

describe("A3 directory i18n helpers", () => {
  it("maps weekday 0 to Monday chrome, not Sunday", async () => {
    await i18n.changeLanguage("en");
    expect(weekdayLabelMonFirst(0)).toBe("Mon");
    expect(weekdayLabelMonFirst(6)).toBe("Sun");
  });

  it("maps known service categories to EN chrome, not API tokens", async () => {
    await i18n.changeLanguage("en");
    expect(serviceCategoryLabel("therapy")).toBe("Therapy");
    expect(serviceCategoryLabel("THERAPY")).toBe("Therapy");
    expect(serviceCategoryLabel(null)).toBe("");
  });

  it("directory enum keys are EN by default", () => {
    expect(i18n.t("clinics.types.stomatology", { ns: "directory" })).toBe("Dentistry");
    expect(i18n.t("doctorDrawer.roles.doctor", { ns: "directory" })).toBe("Doctor");
    expect(i18n.t("staff.deleteCategoryTitle", { ns: "directory" })).toBe(
      "Delete profession category?",
    );
  });
});
