import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface FeedPost {
  id: string;
  clinic_id: string;
  title: string;
  body: string;
  image_url: string | null;
  video_url?: string | null;
  additional_image_urls?: string[] | null;
  link: string | null;
  published_at: string | null;
  created_at: string;
}

export interface FeedStory {
  id: string;
  clinic_id: string;
  media_type?: string;
  media_url: string;
  caption: string | null;
  order_index: number;
  expires_at: string | null;
  created_at: string;
}

export function usePublicFeed(clinicId: string | null) {
  return useQuery({
    queryKey: ["public", "clinics", clinicId, "feed"],
    queryFn: () =>
      api.get<FeedPost[]>(`/v1/public/clinics/${clinicId}/feed`),
    enabled: !!clinicId,
  });
}

export function usePublicStories(clinicId: string | null) {
  return useQuery({
    queryKey: ["public", "clinics", clinicId, "stories"],
    queryFn: () =>
      api.get<FeedStory[]>(`/v1/public/clinics/${clinicId}/stories`),
    enabled: !!clinicId,
  });
}
