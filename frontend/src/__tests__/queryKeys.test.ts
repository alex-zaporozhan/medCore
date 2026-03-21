import { describe, expect, it } from "vitest";
import { queryKeys } from "@/queryKeys";

/**
 * Регресс §5: стабильность кортежей ключей для инвалидации и optimistic-обновлений.
 */
describe("queryKeys", () => {
  it("CRM: leads list key совпадает с префиксом + filters", () => {
    const filters = { projection: "kanban" as const, stage_id: "s1" };
    const key = [...queryKeys.crm.leadsListPrefix, filters];
    expect(key[0]).toBe("crm-leads");
    expect(key[1]).toBe(filters);
  });

  it("CRM: kanban infinite key совпадает с историческим кортежем", () => {
    expect(queryKeys.crm.kanbanInfinite("st", "open", "q", 40)).toEqual([
      "crm-leads-kanban",
      "st",
      "open",
      "q",
      40,
    ]);
  });

  it("adminTasks: open и list — разные ключи", () => {
    expect(queryKeys.adminTasks.open()).toEqual(["admin-tasks", "open"]);
    expect(queryKeys.adminTasks.list()).toEqual(["admin-tasks"]);
  });

  it("adminAi: clinicSettings включает clinicId", () => {
    expect(queryKeys.adminAi.clinicSettings("cl-1")).toEqual([
      "admin",
      "clinics",
      "cl-1",
      "ai-settings",
    ]);
  });
});
