import { describe, expect, it } from "vitest";
import {
  apiErrorCode,
  bookingErrorI18nKey,
  commonErrorI18nKey,
  adminQueryErrorI18nKey,
  isAdminChromePath,
  isEmptyClinicDatabaseError,
} from "../errors";

describe("apiErrorCode", () => {
  it("ignores an empty code property so uncoded API detail is not treated as mapped", () => {
    expect(apiErrorCode({ code: undefined, message: "slot taken" })).toBeUndefined();
    expect(apiErrorCode({ code: "", message: "slot taken" })).toBeUndefined();
    expect(apiErrorCode({ code: "slot_unavailable" })).toBe("slot_unavailable");
  });
});

describe("bookingErrorI18nKey", () => {
  it("maps known booking codes and does not invent a generic key when code is missing", () => {
    expect(bookingErrorI18nKey("slot_unavailable", "booking")).toBe("errors.slotUnavailable");
    expect(bookingErrorI18nKey(undefined, "booking")).toBeNull();
    expect(bookingErrorI18nKey("patient_not_found", "booking")).toBeNull();
  });

  it("maps known payment codes and leaves uncoded payment errors to formatQueryError", () => {
    expect(bookingErrorI18nKey("payment_failed", "payment")).toBe("errors.paymentFailed");
    expect(bookingErrorI18nKey(undefined, "payment")).toBeNull();
  });
});

describe("commonErrorI18nKey / isAdminChromePath", () => {
  it("maps known admin codes and leaves unknown codes to formatQueryError", () => {
    expect(commonErrorI18nKey("forbidden")).toBe("errors.forbidden");
    expect(commonErrorI18nKey("empty_db_no_clinic")).toBe("errors.empty_db_no_clinic");
    expect(commonErrorI18nKey("method_not_allowed")).toBe("errors.method_not_allowed");
    expect(commonErrorI18nKey("unauthorized")).toBe("errors.unauthorized");
    expect(commonErrorI18nKey("invalid_credentials")).toBe("errors.invalid_credentials");
    expect(commonErrorI18nKey("billing_revoked")).toBe("errors.billing_revoked");
    expect(commonErrorI18nKey("empty_db_no_clinic")).toBe("errors.empty_db_no_clinic");
    expect(commonErrorI18nKey("slot_unavailable")).toBeNull();
    expect(commonErrorI18nKey(undefined)).toBeNull();
  });

  it("treats only /admin* as admin chrome", () => {
    expect(isAdminChromePath("/admin")).toBe(true);
    expect(isAdminChromePath("/admin/settings")).toBe(true);
    expect(isAdminChromePath("/app/chat")).toBe(false);
    expect(isAdminChromePath("/login")).toBe(false);
    expect(isAdminChromePath(undefined)).toBe(false);
  });
});

describe("isEmptyClinicDatabaseError", () => {
  it("matches the current RU EMPTY_DB copy and a future code", () => {
    expect(
      isEmptyClinicDatabaseError(
        new Error("В базе данных нет ни одной клиники. Добавьте клинику в разделе настроек."),
      ),
    ).toBe(true);
    expect(isEmptyClinicDatabaseError({ code: "empty_db_no_clinic" })).toBe(true);
    expect(isEmptyClinicDatabaseError(new Error("slot already taken"))).toBe(false);
    expect(
      isEmptyClinicDatabaseError(new Error("Нет доступа к этой клинике. Выберите другую.")),
    ).toBe(false);
    expect(isEmptyClinicDatabaseError(new Error("поликлиника недоступна"))).toBe(false);
  });
});

describe("adminQueryErrorI18nKey", () => {
  it("does not let HTTP not_found hide the empty-clinic 404", () => {
    const emptyDb = Object.assign(
      new Error("В базе данных нет ни одной клиники. Добавьте клинику в разделе настроек."),
      { code: "not_found" },
    );
    expect(adminQueryErrorI18nKey(emptyDb)).toBe("errors.empty_db_no_clinic");
    expect(adminQueryErrorI18nKey(Object.assign(new Error("Service not found"), { code: "not_found" }))).toBe(
      "errors.not_found",
    );
    expect(
      adminQueryErrorI18nKey(Object.assign(new Error("Authentication required"), { code: "unauthorized" })),
    ).toBe("errors.unauthorized");
  });
});

describe("bookingStatusMeta", () => {
  it("does not keep a parallel RU label map (admin chrome is bookings.status.*)", async () => {
    const mod = await import("../bookingStatusMeta");
    expect("BOOKING_STATUS_LABEL_RU" in mod).toBe(false);
  });
});
