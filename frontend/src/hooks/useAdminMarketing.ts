import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface PromoPostRead {
  id: string;
  clinic_id: string;
  title: string;
  body: string;
  image_url: string | null;
  link: string | null;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PromoPostCreate {
  title: string;
  body: string;
  image_url?: string | null;
  link?: string | null;
  is_published?: boolean;
  published_at?: string | null;
}

export interface PromoPostUpdate {
  title?: string;
  body?: string;
  image_url?: string | null;
  link?: string | null;
  is_published?: boolean;
  published_at?: string | null;
}

export interface StoryRead {
  id: string;
  clinic_id: string;
  media_url: string;
  caption: string | null;
  order_index: number;
  expires_at: string | null;
  created_at: string;
}

export interface StoryCreate {
  media_url: string;
  media_type?: "image" | "video";
  caption?: string | null;
  order_index?: number;
  expires_at?: string | null;
}

export interface StoryUpdate {
  media_url?: string;
  caption?: string | null;
  order_index?: number;
  expires_at?: string | null;
}

const marketingKeys = (clinicId: string | null) =>
  ["admin", "clinics", clinicId, "marketing"] as const;

export function useAdminPromoPosts(clinicId: string | null) {
  return useQuery({
    queryKey: [...marketingKeys(clinicId), "posts"],
    queryFn: () =>
      api.get<PromoPostRead[]>(`/v1/admin/clinics/${clinicId}/marketing/posts`),
    enabled: !!clinicId,
  });
}

export function useCreatePromoPost(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PromoPostCreate) =>
      api.post<PromoPostRead>(
        `/v1/admin/clinics/${clinicId}/marketing/posts`,
        body
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketingKeys(clinicId) }),
  });
}

export function useUpdatePromoPost(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, body }: { postId: string; body: PromoPostUpdate }) =>
      api.put<PromoPostRead>(
        `/v1/admin/clinics/${clinicId}/marketing/posts/${postId}`,
        body
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketingKeys(clinicId) }),
  });
}

export function useDeletePromoPost(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/marketing/posts/${postId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketingKeys(clinicId) }),
  });
}

export function useAdminStories(clinicId: string | null) {
  return useQuery({
    queryKey: [...marketingKeys(clinicId), "stories"],
    queryFn: () =>
      api.get<StoryRead[]>(`/v1/admin/clinics/${clinicId}/marketing/stories`),
    enabled: !!clinicId,
  });
}

export function useCreateStory(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StoryCreate) =>
      api.post<StoryRead>(
        `/v1/admin/clinics/${clinicId}/marketing/stories`,
        body
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketingKeys(clinicId) }),
  });
}

export function useUpdateStory(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ storyId, body }: { storyId: string; body: StoryUpdate }) =>
      api.put<StoryRead>(
        `/v1/admin/clinics/${clinicId}/marketing/stories/${storyId}`,
        body
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketingKeys(clinicId) }),
  });
}

export function useDeleteStory(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (storyId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/marketing/stories/${storyId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketingKeys(clinicId) }),
  });
}
