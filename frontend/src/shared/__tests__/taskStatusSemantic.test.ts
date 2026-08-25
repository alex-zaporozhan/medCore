import { describe, it, expect } from "vitest";
import { taskKanbanQuietSurface, taskStatusCardSurface } from "../taskStatusSemantic";

describe("taskKanbanQuietSurface", () => {
  it("uses quiet hairline surface without tint or shadow", () => {
    const quiet = taskKanbanQuietSurface();
    expect(quiet.boxShadow).toBe("none");
    expect(quiet.border).toBe("1px solid var(--calendar-card-border)");
    expect(quiet.background).toBe("var(--bg-card, #fff)");
    expect(quiet).not.toHaveProperty("borderLeftWidth");
  });

  it("differs from details status surface (left bar + shadow)", () => {
    const details = taskStatusCardSurface("open");
    const quiet = taskKanbanQuietSurface();
    expect(details.boxShadow).not.toBe("none");
    expect(details.borderLeftWidth).toBe("var(--calendar-bar-width)");
    expect(quiet.boxShadow).toBe("none");
  });
});
