import { describe, expect, it } from "vitest";

import {
  flattenOmniMessagePages,
  mergeOmniMessagesById,
  type OmniMessageLike,
} from "../mergeOmniMessages";

function m(id: string, created: string): OmniMessageLike {
  return { id, created_at: created };
}

describe("mergeOmniMessagesById", () => {
  it("merges disjoint batches in chronological order", () => {
    const a = [m("1", "2025-01-01T10:00:00Z"), m("2", "2025-01-01T11:00:00Z")];
    const b = [m("3", "2025-01-01T12:00:00Z")];
    expect(mergeOmniMessagesById(a, b)).toEqual([m("1", "2025-01-01T10:00:00Z"), m("2", "2025-01-01T11:00:00Z"), m("3", "2025-01-01T12:00:00Z")]);
  });

  it("dedupes by id; incoming wins by default", () => {
    const prev = [m("1", "2025-01-01T10:00:00Z")];
    const inc = [m("1", "2025-01-01T10:30:00Z")];
    expect(mergeOmniMessagesById(prev, inc)).toEqual([m("1", "2025-01-01T10:30:00Z")]);
  });

  it("dedupes by id; previous wins when prefer previous", () => {
    const prev = [m("1", "2025-01-01T10:00:00Z")];
    const inc = [m("1", "2025-01-01T10:30:00Z")];
    expect(mergeOmniMessagesById(prev, inc, "previous")).toEqual([m("1", "2025-01-01T10:00:00Z")]);
  });
});

describe("flattenOmniMessagePages", () => {
  it("orders TanStack infinite pages (newest page first) into chronological list", () => {
    const pages = [
      { items: [m("2", "2025-01-01T11:00:00Z"), m("3", "2025-01-01T12:00:00Z")] },
      { items: [m("1", "2025-01-01T10:00:00Z")] },
    ];
    expect(flattenOmniMessagePages(pages)).toEqual([
      m("1", "2025-01-01T10:00:00Z"),
      m("2", "2025-01-01T11:00:00Z"),
      m("3", "2025-01-01T12:00:00Z"),
    ]);
  });
});
