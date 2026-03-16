/**
 * Admin global search (patients, bookings). Used by Spotlight.
 * Contract: GET /api/v1/admin/search?q=... when backend is ready.
 * Stub: returns empty array until API exists.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { getAdminToken } from "@/api/client";

export interface AdminSearchHit {
  id: string;
  type: "patient" | "booking";
  label: string;
  description?: string;
  to: string;
}

export interface AdminSearchResponse {
  items: AdminSearchHit[];
}

export function useAdminSearch(query: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: ["admin", "search", query ?? ""],
    queryFn: async (): Promise<AdminSearchResponse> => {
      if (!query || query.trim().length < 2) return { items: [] };
      try {
        const res = await api.get<AdminSearchResponse>(
          `/v1/admin/search?q=${encodeURIComponent(query.trim())}`,
          token
        );
        return res ?? { items: [] };
      } catch {
        return { items: [] };
      }
    },
    enabled: !!token && !!query && query.trim().length >= 2,
    staleTime: 30_000,
  });
}
