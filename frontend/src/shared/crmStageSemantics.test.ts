import { describe, expect, it } from "vitest";
import {
  buildSemanticMapFromResolved,
  buildStageIdToSemantic,
  canTransitionSemantic,
  CRM_SEM,
} from "./crmStageSemantics";

describe("crmStageSemantics", () => {
  it("allows same semantic", () => {
    expect(canTransitionSemantic(CRM_SEM.START, CRM_SEM.START)).toBe(true);
  });

  it("allows start -> scheduled", () => {
    expect(canTransitionSemantic(CRM_SEM.START, CRM_SEM.SCHEDULED)).toBe(true);
  });

  it("blocks start -> won", () => {
    expect(canTransitionSemantic(CRM_SEM.START, CRM_SEM.WON)).toBe(false);
  });

  it("allows scheduled -> won", () => {
    expect(canTransitionSemantic(CRM_SEM.SCHEDULED, CRM_SEM.WON)).toBe(true);
  });

  it("buildStageIdToSemantic maps last duplicate semantic to stage (API one row per semantic)", () => {
    const map = buildStageIdToSemantic([
      { semantic: "start", stage_id: "a" },
      { semantic: "won", stage_id: "b" },
    ]);
    expect(map.a).toBe("start");
    expect(map.b).toBe("won");
  });

  it("buildSemanticMapFromResolved skips null semantics", () => {
    const map = buildSemanticMapFromResolved([
      { stage_id: "x", semantic: "start" },
      { stage_id: "y", semantic: null },
    ]);
    expect(map.x).toBe("start");
    expect(map.y).toBeUndefined();
  });
});
