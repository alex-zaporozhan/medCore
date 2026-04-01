import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface RbacPermissionRead {
  id: string;
  code: string;
  description: string | null;
  domain: string;
}

export interface RbacRoleRead {
  id: string;
  code: string;
  name: string;
  clinic_id: string | null;
  permission_codes: string[];
}

export interface RbacRolePresetRead {
  code: string;
  permission_codes: string[];
}

export interface RbacCatalogResponse {
  roles: RbacRoleRead[];
  permissions: RbacPermissionRead[];
  role_presets: RbacRolePresetRead[];
}

export interface RbacUserPermissionOverrideRead {
  permission_code: string;
  effect: "grant" | "deny";
}

export interface RbacUserRead {
  admin_id: string;
  full_name: string | null;
  email: string;
  role_codes: string[];
  direct_overrides: RbacUserPermissionOverrideRead[];
  effective_permission_codes: string[];
}

export interface RbacUsersResponse {
  items: RbacUserRead[];
}

export interface RbacPolicyRead {
  allow_patient_disable_discount_notifications: boolean;
  allow_patient_disable_reminders: boolean;
  allow_patient_disable_all_notifications: boolean;
  owner_morning_brief_enabled: boolean;
  morning_brief_send_at_utc: string | null;
  owner_telegram_chat_id: string | null;
  ai_supervisor_enabled: boolean;
  ai_supervisor_send_at_utc: string | null;
  ai_supervisor_recipient_chat_ids: string[];
}

export interface RbacAuditLogRead {
  id: string;
  actor_admin_id: string | null;
  actor_admin_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before_payload: Record<string, unknown> | null;
  after_payload: Record<string, unknown> | null;
  note: string | null;
  created_at: string;
}

/** Query string for RBAC endpoints when acting on a clinic other than JWT home (owner network). */
function rbacEffectiveQuery(effectiveClinicId?: string | null): string {
  if (!effectiveClinicId) return "";
  return `?effective_clinic_id=${encodeURIComponent(effectiveClinicId)}`;
}

/** Matches backend ``locale_from_accept_language`` (ru vs en error messages). */
function rbacAcceptLanguageHeader(uiLocale?: string | null): Record<string, string> {
  if (uiLocale === "ru") {
    return { "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8" };
  }
  return { "Accept-Language": "en-US,en;q=0.9,ru;q=0.6" };
}

export function useRbacCatalog(effectiveClinicId?: string | null, queryEnabled = true) {
  return useQuery({
    queryKey: queryKeys.rbac.catalog(effectiveClinicId),
    queryFn: () =>
      api.get<RbacCatalogResponse>(`/v1/admin/rbac/catalog${rbacEffectiveQuery(effectiveClinicId)}`),
    enabled: queryEnabled && Boolean(effectiveClinicId),
  });
}

export function useRbacUsers(effectiveClinicId?: string | null) {
  return useQuery({
    queryKey: queryKeys.rbac.users(effectiveClinicId),
    queryFn: () =>
      api.get<RbacUsersResponse>(`/v1/admin/rbac/users${rbacEffectiveQuery(effectiveClinicId)}`),
  });
}

export function useRbacPolicies(effectiveClinicId?: string | null) {
  return useQuery({
    queryKey: queryKeys.rbac.policies(effectiveClinicId),
    queryFn: () =>
      api.get<RbacPolicyRead>(`/v1/admin/rbac/policies${rbacEffectiveQuery(effectiveClinicId)}`),
  });
}

export function useRbacAudit(limit = 100, effectiveClinicId?: string | null) {
  const qs = new URLSearchParams();
  qs.set("limit", String(limit));
  if (effectiveClinicId) qs.set("effective_clinic_id", effectiveClinicId);
  return useQuery({
    queryKey: queryKeys.rbac.audit(limit, effectiveClinicId),
    queryFn: () =>
      api.get<RbacAuditLogRead[]>(`/v1/admin/rbac/audit?${qs.toString()}`),
  });
}

export function useCreateClinicRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      code: string;
      name: string;
      description?: string | null;
      permission_codes: string[];
      note?: string | null;
      effectiveClinicId?: string | null;
      /** Page UI language — sent as Accept-Language for API error messages */
      uiLocale?: string | null;
    }) =>
      api.post<RbacRoleRead>(
        `/v1/admin/rbac/roles${rbacEffectiveQuery(vars.effectiveClinicId)}`,
        {
          code: vars.code,
          name: vars.name,
          description: vars.description ?? null,
          permission_codes: vars.permission_codes,
          note: vars.note ?? null,
        },
        undefined,
        rbacAcceptLanguageHeader(vars.uiLocale)
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
      void qc.invalidateQueries({ queryKey: queryKeys.adminSession() });
      void qc.invalidateQueries({ queryKey: ["staff-directory"] });
    },
  });
}

export function useDeleteClinicRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      roleId: string;
      effectiveClinicId?: string | null;
      uiLocale?: string | null;
    }) =>
      api.delete<void>(
        `/v1/admin/rbac/roles/${vars.roleId}${rbacEffectiveQuery(vars.effectiveClinicId)}`,
        undefined,
        rbacAcceptLanguageHeader(vars.uiLocale)
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
      void qc.invalidateQueries({ queryKey: queryKeys.adminSession() });
      void qc.invalidateQueries({ queryKey: ["staff-directory"] });
    },
  });
}

export function usePatchRolePermissions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      roleId: string;
      permission_codes: string[];
      note?: string | null;
      effectiveClinicId?: string | null;
    }) =>
      api.patch<{ ok: boolean }>(
        `/v1/admin/rbac/roles/${vars.roleId}/permissions${rbacEffectiveQuery(vars.effectiveClinicId)}`,
        {
          permission_codes: vars.permission_codes,
          note: vars.note ?? null,
        }
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
      void qc.invalidateQueries({ queryKey: queryKeys.adminSession() });
    },
  });
}

export function usePatchUserRoles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      userId: string;
      role_codes: string[];
      note?: string | null;
      effectiveClinicId?: string | null;
    }) =>
      api.patch<{ ok: boolean }>(
        `/v1/admin/rbac/users/${vars.userId}/roles${rbacEffectiveQuery(vars.effectiveClinicId)}`,
        {
          role_codes: vars.role_codes,
          note: vars.note ?? null,
        }
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
      void qc.invalidateQueries({ queryKey: queryKeys.adminSession() });
    },
  });
}

export function usePatchUserPermissions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      userId: string;
      overrides: { permission_code: string; effect: "grant" | "deny" }[];
      note?: string | null;
      effectiveClinicId?: string | null;
    }) =>
      api.patch<{ ok: boolean }>(
        `/v1/admin/rbac/users/${vars.userId}/permissions${rbacEffectiveQuery(vars.effectiveClinicId)}`,
        {
          overrides: vars.overrides,
          note: vars.note ?? null,
        }
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
      void qc.invalidateQueries({ queryKey: queryKeys.adminSession() });
    },
  });
}

export function usePatchRbacPolicies() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<RbacPolicyRead> & {
      note?: string | null;
      effectiveClinicId?: string | null;
    }) => {
      const { effectiveClinicId, ...body } = payload;
      return api.patch<{ ok: boolean }>(
        `/v1/admin/rbac/policies${rbacEffectiveQuery(effectiveClinicId)}`,
        body
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
    },
  });
}
