/**
 * Merge omnichannel message lists by stable id; chronological ascending by created_at.
 * On duplicate id, `prefer` controls which payload wins (refetch / newer page vs stale).
 */
export type OmniMessageLike = {
  id: string;
  created_at: string | null;
};

export function mergeOmniMessagesById(
  previous: OmniMessageLike[],
  incoming: OmniMessageLike[],
  prefer: "incoming" | "previous" = "incoming",
): OmniMessageLike[] {
  const map = new Map<string, OmniMessageLike>();
  if (prefer === "incoming") {
    for (const m of previous) {
      map.set(m.id, m);
    }
    for (const m of incoming) {
      map.set(m.id, m);
    }
  } else {
    for (const m of incoming) {
      map.set(m.id, m);
    }
    for (const m of previous) {
      map.set(m.id, m);
    }
  }
  return Array.from(map.values()).sort(
    (a, b) =>
      new Date(a.created_at ?? 0).getTime() - new Date(b.created_at ?? 0).getTime(),
  );
}

/** Flatten infinite-query pages (newest page first in `pages`) into one chronological list without duplicate ids. */
export function flattenOmniMessagePages<T extends OmniMessageLike>(pages: { items: T[] }[]): T[] {
  const ordered = [...pages].reverse().flatMap((p) => p.items);
  const seen = new Set<string>();
  const out: T[] = [];
  for (const m of ordered) {
    if (seen.has(m.id)) continue;
    seen.add(m.id);
    out.push(m);
  }
  out.sort(
    (a, b) =>
      new Date(a.created_at ?? 0).getTime() - new Date(b.created_at ?? 0).getTime(),
  );
  return out;
}
