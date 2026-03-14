import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  InventoryProduct,
  Warehouse,
  ServiceConsumable,
  InventoryTransaction,
  InventoryStockItem,
} from "@/api/types";

export function useInventoryProducts(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "inventory", "products"],
    queryFn: () =>
      api.get<InventoryProduct[]>(`/v1/admin/clinics/${clinicId}/inventory/products`),
    enabled: !!clinicId,
  });
}

export function useWarehouses(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "inventory", "warehouses"],
    queryFn: () =>
      api.get<Warehouse[]>(`/v1/admin/clinics/${clinicId}/inventory/warehouses`),
    enabled: !!clinicId,
  });
}

export function useServiceConsumables(
  clinicId: string | null,
  serviceId: string | null
) {
  return useQuery({
    queryKey: [
      "admin",
      "clinics",
      clinicId,
      "inventory",
      "service-consumables",
      serviceId,
    ],
    queryFn: () =>
      api.get<ServiceConsumable[]>(
        `/v1/admin/clinics/${clinicId}/inventory/services/${serviceId}/consumables`
      ),
    enabled: !!clinicId && !!serviceId,
  });
}

export function useInventoryTransactions(
  clinicId: string | null,
  productId: string | null,
  warehouseId: string | null,
  dateFrom: string | null = null,
  dateTo: string | null = null
) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  if (warehouseId) params.set("warehouse_id", warehouseId);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const qs = params.toString();

  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "inventory", "transactions", qs],
    queryFn: () =>
      api.get<InventoryTransaction[]>(
        `/v1/admin/clinics/${clinicId}/inventory/transactions${qs ? `?${qs}` : ""}`
      ),
    enabled: !!clinicId,
  });
}

export function useInventoryStock(
  clinicId: string | null,
  productId: string | null,
  warehouseId: string | null
) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  if (warehouseId) params.set("warehouse_id", warehouseId);
  const qs = params.toString();

  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "inventory", "stock", qs],
    queryFn: () =>
      api.get<InventoryStockItem>(
        `/v1/admin/clinics/${clinicId}/inventory/stock${qs ? `?${qs}` : ""}`
      ),
    enabled: !!clinicId && !!productId && !!warehouseId,
  });
}

