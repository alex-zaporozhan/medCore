import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface StaffProfessionCategoryRow {
  id: string;
  clinic_id: string;
  name: string;
  sort_order: number;
  default_role_codes: string[];
  created_at: string;
}

export interface StaffDirectoryAdminRow {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string | null;
  birth_date?: string | null;
  employment_status: string;
  profession_category_id: string | null;
  profession_category_name: string | null;
}

export function useStaffProfessionCategories(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.staffDirectory.professionCategories(clinicId),
    queryFn: () =>
      api.get<StaffProfessionCategoryRow[]>(
        `/v1/admin/clinics/${clinicId}/staff-directory/profession-categories`
      ),
    enabled: Boolean(clinicId),
  });
}

export function useCreateStaffProfessionCategoryMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; sort_order?: number; default_role_codes: string[] }) =>
      api.post<StaffProfessionCategoryRow>(
        `/v1/admin/clinics/${clinicId}/staff-directory/profession-categories`,
        body
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffDirectory.professionCategories(clinicId) });
    },
  });
}

export function usePatchStaffProfessionCategoryMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      categoryId: string;
      name?: string;
      sort_order?: number;
      default_role_codes?: string[];
    }) => {
      const body: Record<string, unknown> = {};
      if (args.name !== undefined) body.name = args.name;
      if (args.sort_order !== undefined) body.sort_order = args.sort_order;
      if (args.default_role_codes !== undefined) body.default_role_codes = args.default_role_codes;
      return api.patch<StaffProfessionCategoryRow>(
        `/v1/admin/clinics/${clinicId}/staff-directory/profession-categories/${args.categoryId}`,
        body
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffDirectory.professionCategories(clinicId) });
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
    },
  });
}

export function useDeleteStaffProfessionCategoryMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (categoryId: string) =>
      api.delete(
        `/v1/admin/clinics/${clinicId}/staff-directory/profession-categories/${categoryId}`
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffDirectory.professionCategories(clinicId) });
    },
  });
}

export function useStaffDirectoryAdmins(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.staffDirectory.admins(clinicId),
    queryFn: () =>
      api.get<StaffDirectoryAdminRow[]>(`/v1/admin/clinics/${clinicId}/staff-directory/admins`),
    enabled: Boolean(clinicId),
  });
}

export function useCreateStaffDirectoryAdminMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      email: string;
      password: string;
      full_name?: string | null;
      birth_date?: string | null;
      profession_category_id?: string | null;
      role_codes: string[];
    }) =>
      api.post<StaffDirectoryAdminRow>(
        `/v1/admin/clinics/${clinicId}/staff-directory/admins`,
        body
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffDirectory.admins(clinicId) });
      void qc.invalidateQueries({ queryKey: queryKeys.adminAdmins.list() });
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
    },
  });
}

export function usePatchStaffDirectoryAdminMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      adminId: string;
      employment_status?: "active" | "terminated";
      profession_category_id?: string | null;
    }) => {
      const body: Record<string, unknown> = {};
      if (args.employment_status !== undefined) body.employment_status = args.employment_status;
      if (args.profession_category_id !== undefined) body.profession_category_id = args.profession_category_id;
      return api.patch<StaffDirectoryAdminRow>(
        `/v1/admin/clinics/${clinicId}/staff-directory/admins/${args.adminId}`,
        body
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffDirectory.admins(clinicId) });
      void qc.invalidateQueries({ queryKey: queryKeys.adminAdmins.list() });
      void qc.invalidateQueries({ queryKey: queryKeys.rbac.prefix });
      void qc.invalidateQueries({ queryKey: queryKeys.adminSession() });
    },
  });
}
