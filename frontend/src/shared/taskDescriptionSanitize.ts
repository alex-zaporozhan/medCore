/**
 * Strip machine trace/event suffixes from task descriptions shown to operators.
 * Bare UUIDs without trace_id=/event_id= prefixes are intentionally preserved.
 */
export function sanitizeTaskDescription(text: string): string {
  return text
    .replace(/\s*trace_id=[0-9a-fA-F-]{8,}(?:\s+event_id=[0-9a-fA-F-]{8,})?\.?/g, "")
    .replace(/\s*event_id=[0-9a-fA-F-]{8,}\.?/g, "")
    .trim();
}
