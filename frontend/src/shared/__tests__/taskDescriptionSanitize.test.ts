import { describe, it, expect } from "vitest";
import { sanitizeTaskDescription } from "../taskDescriptionSanitize";

describe("sanitizeTaskDescription", () => {
  it("removes trace_id and paired event_id suffix", () => {
    const raw =
      "Patient no-show follow-up trace_id=550e8400-e29b-41d4-a716-446655440000 event_id=6ba7b810-9dad-11d1-80b4-00c04fd430c8.";
    expect(sanitizeTaskDescription(raw)).toBe("Patient no-show follow-up");
  });

  it("removes standalone event_id suffix", () => {
    const raw = "ERP sync failed event_id=6ba7b810-9dad-11d1-80b4-00c04fd430c8.";
    expect(sanitizeTaskDescription(raw)).toBe("ERP sync failed");
  });

  it("preserves bare UUID without trace_id/event_id prefix", () => {
    const bare = "Reference 550e8400-e29b-41d4-a716-446655440000 in notes";
    expect(sanitizeTaskDescription(bare)).toBe(bare);
  });

  it("trims whitespace after stripping", () => {
    expect(sanitizeTaskDescription("  Hello trace_id=550e8400-e29b-41d4-a716-446655440000  ")).toBe("Hello");
  });
});
