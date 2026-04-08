import { resolveProductFeatures } from "@/config/features";
import { useAdminSession } from "@/hooks/useAdminSession";
import type { ProductFeatures } from "@/config/features";

/** UI-флаги с учётом SaaS entitlements; без org — как legacy (всё включено). */
export function useProductFeatures(): ProductFeatures {
  const { data: session } = useAdminSession();
  return resolveProductFeatures(session);
}
