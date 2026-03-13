import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface StickerItem {
  key: string;
  url: string;
}

export interface StickerSetsResponse {
  sets: Record<string, StickerItem[]>;
}

/** Fetch sticker sets (public, no auth). Returns key -> url map for "default" set. */
export function useStickerSets(enabled: boolean) {
  const q = useQuery({
    queryKey: ["stickers-sets"],
    queryFn: () => api.get<StickerSetsResponse>("/v1/stickers/sets", null),
    enabled,
  });
  const defaultList = q.data?.sets?.default ?? [];
  const keyToUrl: Record<string, string> = {};
  defaultList.forEach(({ key, url }) => {
    keyToUrl[key] = url;
  });
  return { ...q, stickerKeyToUrl: keyToUrl, defaultStickers: defaultList };
}
