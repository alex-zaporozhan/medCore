/**
 * Client-side mirror of `LeadStageStateMachine` / semantics (CRM_AI_009, QA_ARCH W4.2 D4).
 * Keep in sync with `src/application/services/lead_stage_state_machine.py`.
 */

export const CRM_SEM = {
  START: "start",
  SCHEDULED: "scheduled",
  STALE: "stale",
  WON: "won",
  LOST: "lost",
} as const;

function norm(s: string | null | undefined): string {
  return (s || "").trim().toLowerCase();
}

/** Allowed transitions between semantic codes (same rules as backend). */
export function canTransitionSemantic(
  fromSemantic: string | null | undefined,
  toSemantic: string | null | undefined
): boolean {
  const f = norm(fromSemantic);
  const t = norm(toSemantic);
  if (!f || !t) return false;
  if (f === t) return true;

  const rules: { from: string[]; to: string[] }[] = [
    { from: [CRM_SEM.START], to: [CRM_SEM.SCHEDULED, CRM_SEM.STALE, CRM_SEM.LOST] },
    { from: [CRM_SEM.SCHEDULED], to: [CRM_SEM.WON, CRM_SEM.LOST, CRM_SEM.STALE] },
    { from: [CRM_SEM.STALE], to: [CRM_SEM.SCHEDULED, CRM_SEM.WON, CRM_SEM.LOST] },
    { from: [CRM_SEM.WON], to: [CRM_SEM.WON] },
    { from: [CRM_SEM.LOST], to: [CRM_SEM.LOST] },
  ];

  for (const rule of rules) {
    if (rule.from.includes(f) && rule.to.includes(t)) return true;
  }
  return false;
}

/** Invert API mappings to stage_id → semantic. */
export function buildStageIdToSemantic(
  mappings: { semantic: string; stage_id: string }[]
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of mappings) {
    out[m.stage_id] = m.semantic;
  }
  return out;
}

/**
 * Prefer `resolved_stage_semantics` from GET .../stage-semantics (mapping + infer, server-side).
 */
export function buildSemanticMapFromResolved(
  resolved: { stage_id: string; semantic: string | null }[]
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const r of resolved) {
    if (r.semantic) out[r.stage_id] = r.semantic;
  }
  return out;
}
