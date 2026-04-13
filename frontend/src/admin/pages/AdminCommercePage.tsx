import { API_BASE, getAdminToken } from "@/api/client";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useClinics, useUpdateClinicMutation } from "@/hooks";
import { useAdminSession } from "@/hooks/useAdminSession";
import { AdminSettingsSectionCard, ContextBar } from "@/shared/ui";
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Code,
  FileInput,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  ThemeIcon,
} from "@mantine/core";
import { IconShoppingBag } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type Overview = {
  clinic_id: string;
  organization_id: string;
  stock_locations_count: number;
  nomenclature_items_count: number;
};

type NetworkClinicRow = {
  clinic_id: string;
  clinic_name: string;
  stock_locations_count: number;
  nomenclature_items_count: number;
  total_on_hand_quantity: string | number;
};

type NetworkOverview = {
  organization_id: string;
  clinics: NetworkClinicRow[];
  totals: {
    stock_locations_total: number;
    nomenclature_items_total: number;
    total_on_hand_quantity: string | number;
  };
};

type ImportJobRow = {
  id: string;
  source_profile: string;
  status: string;
  idempotency_key: string;
  file_name: string | null;
  created_at: string;
  payload_summary?: Record<string, unknown> | null;
  last_error?: string | null;
};

type StockLocationRow = {
  id: string;
  name: string;
  code: string | null;
  is_default: boolean;
  created_at: string;
};

type NomenclatureRow = {
  id: string;
  name: string;
  sku: string | null;
  unit: string;
  is_active: boolean;
  created_at: string;
};

type BalanceLineRow = {
  balance_id: string | null;
  nomenclature_item_id: string;
  sku: string | null;
  name: string;
  unit: string;
  quantity: string | number;
};

type MovementRow = {
  id: string;
  stock_location_id: string;
  to_stock_location_id?: string | null;
  doc_kind: string;
  remark: string | null;
  created_at: string;
};

type MovementDetail = MovementRow & {
  lines: Array<{
    nomenclature_item_id: string;
    sku: string | null;
    name: string;
    unit: string;
    quantity: string | number;
  }>;
};

async function parseJsonError(r: Response): Promise<string | null> {
  const data = await r.json().catch(() => ({}));
  const code =
    typeof data?.detail === "object" && data.detail?.code
      ? String(data.detail.code)
      : data?.code;
  return code ? String(code) : null;
}

export default function AdminCommercePage() {
  const { data: adminSession } = useAdminSession();
  const { currentClinicId } = useAdminClinic();
  const { data: clinics } = useClinics();
  const updateClinic = useUpdateClinicMutation();
  const activeClinic = useMemo(
    () => clinics?.find((c) => c.id === currentClinicId) ?? null,
    [clinics, currentClinicId],
  );
  const [storeVisible, setStoreVisible] = useState(false);
  const [storeTitle, setStoreTitle] = useState("");
  const [storeSubtitle, setStoreSubtitle] = useState("");
  const [storeSaving, setStoreSaving] = useState(false);
  const orgReady = Boolean(adminSession?.organization_id);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [networkOverview, setNetworkOverview] = useState<NetworkOverview | null>(null);
  const [locations, setLocations] = useState<StockLocationRow[]>([]);
  const [nomenclature, setNomenclature] = useState<NomenclatureRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [locName, setLocName] = useState("");
  const [locCode, setLocCode] = useState("");
  const [locDefault, setLocDefault] = useState(false);
  const [locSubmitting, setLocSubmitting] = useState(false);
  const [nomModalOpen, setNomModalOpen] = useState(false);
  const [editNom, setEditNom] = useState<NomenclatureRow | null>(null);
  const [editNomName, setEditNomName] = useState("");
  const [editNomSku, setEditNomSku] = useState("");
  const [editNomUnit, setEditNomUnit] = useState("pcs");
  const [nomEditSubmitting, setNomEditSubmitting] = useState(false);
  const [balanceLocId, setBalanceLocId] = useState<string | null>(null);
  const [balanceLines, setBalanceLines] = useState<BalanceLineRow[]>([]);
  const [balanceLoading, setBalanceLoading] = useState(false);
  const [pendingQty, setPendingQty] = useState<Record<string, string>>({});
  const [savingBalanceItemId, setSavingBalanceItemId] = useState<string | null>(null);
  const [movements, setMovements] = useState<MovementRow[]>([]);
  const [movModalOpen, setMovModalOpen] = useState(false);
  const [movDetail, setMovDetail] = useState<MovementDetail | null>(null);
  const [movDetailLoading, setMovDetailLoading] = useState(false);
  const [movFormLocId, setMovFormLocId] = useState<string | null>(null);
  const [movToLocId, setMovToLocId] = useState<string | null>(null);
  const [movKind, setMovKind] = useState<"goods_in" | "goods_out" | "goods_transfer">("goods_in");
  const [movRemark, setMovRemark] = useState("");
  const [movRows, setMovRows] = useState<{ itemId: string; qty: string }[]>([{ itemId: "", qty: "1" }]);
  const [movSubmitting, setMovSubmitting] = useState(false);
  const [importCsvBusy, setImportCsvBusy] = useState(false);
  const [importCsvSummary, setImportCsvSummary] = useState<string | null>(null);
  const [importBalanceBusy, setImportBalanceBusy] = useState(false);
  const [importBalanceSummary, setImportBalanceSummary] = useState<string | null>(null);
  const [importJobs, setImportJobs] = useState<ImportJobRow[]>([]);

  const authHeaders = useCallback(() => {
    const token = getAdminToken();
    if (!token) return null;
    return { Authorization: `Bearer ${token}` } as Record<string, string>;
  }, []);

  const load = useCallback(async () => {
    if (!currentClinicId || !orgReady) return;
    const h = authHeaders();
    if (!h) return;
    setLoading(true);
    setError(null);
    try {
      const [ro, rl, rn, rmov, rnet, rjobs] = await Promise.all([
        fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/overview`, { headers: h }),
        fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations`, { headers: h }),
        fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/nomenclature`, { headers: h }),
        fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/movements`, { headers: h }),
        fetch(`${API_BASE}/v1/admin/organization/commerce/network-overview`, { headers: h }),
        fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/import-jobs?limit=30`, {
          headers: h,
        }),
      ]);
      const fail = async (r: Response) => {
        setError((await parseJsonError(r)) ?? r.statusText);
        setOverview(null);
        setNetworkOverview(null);
        setLocations([]);
        setNomenclature([]);
        setMovements([]);
        setImportJobs([]);
      };
      if (!ro.ok) {
        await fail(ro);
        return;
      }
      if (!rl.ok) {
        await fail(rl);
        return;
      }
      if (!rn.ok) {
        await fail(rn);
        return;
      }
      if (!rmov.ok) {
        await fail(rmov);
        return;
      }
      if (!rnet.ok) {
        await fail(rnet);
        return;
      }
      if (!rjobs.ok) {
        await fail(rjobs);
        return;
      }
      setOverview((await ro.json()) as Overview);
      setNetworkOverview((await rnet.json()) as NetworkOverview);
      setLocations((await rl.json()) as StockLocationRow[]);
      setNomenclature((await rn.json()) as NomenclatureRow[]);
      setMovements((await rmov.json()) as MovementRow[]);
      setImportJobs((await rjobs.json()) as ImportJobRow[]);
    } finally {
      setLoading(false);
    }
  }, [currentClinicId, orgReady, authHeaders]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!activeClinic) return;
    setStoreVisible(Boolean(activeClinic.patient_store_visible));
    setStoreTitle(activeClinic.patient_store_title ?? "");
    setStoreSubtitle(activeClinic.patient_store_subtitle ?? "");
  }, [
    activeClinic?.id,
    activeClinic?.patient_store_visible,
    activeClinic?.patient_store_title,
    activeClinic?.patient_store_subtitle,
  ]);

  useEffect(() => {
    if (!locations.length) {
      setBalanceLocId(null);
      setBalanceLines([]);
      setPendingQty({});
      return;
    }
    setBalanceLocId((prev) =>
      prev && locations.some((l) => l.id === prev) ? prev : locations[0].id,
    );
  }, [locations]);

  const loadBalances = useCallback(async () => {
    if (!currentClinicId || !balanceLocId || !orgReady) return;
    const h = authHeaders();
    if (!h) return;
    setBalanceLoading(true);
    setError(null);
    try {
      const r = await fetch(
        `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations/${balanceLocId}/balances`,
        { headers: h },
      );
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        setBalanceLines([]);
        setPendingQty({});
        return;
      }
      const rows = (await r.json()) as BalanceLineRow[];
      setBalanceLines(rows);
      const m: Record<string, string> = {};
      for (const row of rows) {
        m[row.nomenclature_item_id] = String(row.quantity);
      }
      setPendingQty(m);
    } finally {
      setBalanceLoading(false);
    }
  }, [currentClinicId, balanceLocId, orgReady, authHeaders]);

  useEffect(() => {
    void loadBalances();
  }, [loadBalances]);

  useEffect(() => {
    if (!locations.length) {
      setMovFormLocId(null);
      return;
    }
    setMovFormLocId((prev) =>
      prev && locations.some((l) => l.id === prev) ? prev : locations[0].id,
    );
  }, [locations]);

  useEffect(() => {
    if (locations.length < 2 || !movFormLocId) {
      setMovToLocId(null);
      return;
    }
    const others = locations.filter((l) => l.id !== movFormLocId);
    if (!others.length) {
      setMovToLocId(null);
      return;
    }
    setMovToLocId((prev) =>
      prev && others.some((l) => l.id === prev) ? prev : others[0].id,
    );
  }, [locations, movFormLocId]);

  const handleCreateNom = async () => {
    if (!currentClinicId || !name.trim()) return;
    const h = authHeaders();
    if (!h) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/nomenclature`, {
        method: "POST",
        headers: { ...h, "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), sku: sku.trim() || null, unit: "pcs" }),
      });
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      setName("");
      setSku("");
      await load();
      await loadBalances();
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateLoc = async () => {
    if (!currentClinicId || !locName.trim()) return;
    const h = authHeaders();
    if (!h) return;
    setLocSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations`, {
        method: "POST",
        headers: { ...h, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: locName.trim(),
          code: locCode.trim() || null,
          is_default: locDefault,
        }),
      });
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      setLocName("");
      setLocCode("");
      setLocDefault(false);
      await load();
    } finally {
      setLocSubmitting(false);
    }
  };

  const handleDeleteLoc = async (id: string) => {
    if (!currentClinicId) return;
    const h = authHeaders();
    if (!h) return;
    setError(null);
    const r = await fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations/${id}`, {
      method: "DELETE",
      headers: h,
    });
    if (!r.ok) {
      setError((await parseJsonError(r)) ?? r.statusText);
      return;
    }
    await load();
  };

  const handleSetDefaultLoc = async (id: string) => {
    if (!currentClinicId) return;
    const h = authHeaders();
    if (!h) return;
    setError(null);
    const r = await fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations/${id}`, {
      method: "PATCH",
      headers: { ...h, "Content-Type": "application/json" },
      body: JSON.stringify({ is_default: true }),
    });
    if (!r.ok) {
      setError((await parseJsonError(r)) ?? r.statusText);
      return;
    }
    await load();
  };

  const openEditNom = (row: NomenclatureRow) => {
    setEditNom(row);
    setEditNomName(row.name);
    setEditNomSku(row.sku ?? "");
    setEditNomUnit(row.unit || "pcs");
    setNomModalOpen(true);
  };

  const handleSaveEditNom = async () => {
    if (!currentClinicId || !editNom || !editNomName.trim()) return;
    const h = authHeaders();
    if (!h) return;
    setNomEditSubmitting(true);
    setError(null);
    try {
      const r = await fetch(
        `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/nomenclature/${editNom.id}`,
        {
          method: "PATCH",
          headers: { ...h, "Content-Type": "application/json" },
          body: JSON.stringify({
            name: editNomName.trim(),
            unit: editNomUnit.trim() || "pcs",
            sku: editNomSku.trim() || null,
          }),
        },
      );
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      setNomModalOpen(false);
      setEditNom(null);
      await load();
      await loadBalances();
    } finally {
      setNomEditSubmitting(false);
    }
  };

  const handleToggleNomActive = async (row: NomenclatureRow) => {
    if (!currentClinicId) return;
    const h = authHeaders();
    if (!h) return;
    setError(null);
    const r = await fetch(
      `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/nomenclature/${row.id}`,
      {
        method: "PATCH",
        headers: { ...h, "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !row.is_active }),
      },
    );
    if (!r.ok) {
      setError((await parseJsonError(r)) ?? r.statusText);
      return;
    }
    await load();
    await loadBalances();
  };

  const handleSaveBalanceRow = async (itemId: string) => {
    if (!currentClinicId || !balanceLocId) return;
    const h = authHeaders();
    if (!h) return;
    const raw = (pendingQty[itemId] ?? "0").replace(",", ".");
    const num = Number(raw);
    if (Number.isNaN(num) || num < 0) {
      setError("Некорректное количество");
      return;
    }
    setSavingBalanceItemId(itemId);
    setError(null);
    try {
      const r = await fetch(
        `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations/${balanceLocId}/balances/${itemId}`,
        {
          method: "PUT",
          headers: { ...h, "Content-Type": "application/json" },
          body: JSON.stringify({ quantity: num }),
        },
      );
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      await loadBalances();
    } finally {
      setSavingBalanceItemId(null);
    }
  };

  const openMovementDetail = async (docId: string) => {
    if (!currentClinicId) return;
    const h = authHeaders();
    if (!h) return;
    setMovModalOpen(true);
    setMovDetail(null);
    setMovDetailLoading(true);
    setError(null);
    try {
      const r = await fetch(
        `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/movements/${docId}`,
        { headers: h },
      );
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        setMovModalOpen(false);
        return;
      }
      setMovDetail((await r.json()) as MovementDetail);
    } finally {
      setMovDetailLoading(false);
    }
  };

  const handlePostMovement = async () => {
    if (!currentClinicId || !movFormLocId) return;
    if (movKind === "goods_transfer") {
      if (locations.length < 2) {
        setError("Для перемещения нужны минимум две точки");
        return;
      }
      if (!movToLocId || movToLocId === movFormLocId) {
        setError("Выберите точку назначения, отличную от исходной");
        return;
      }
    }
    const h = authHeaders();
    if (!h) return;
    const lines = movRows
      .filter((r) => r.itemId.trim())
      .map((r) => ({
        nomenclature_item_id: r.itemId.trim(),
        quantity: Number(String(r.qty).replace(",", ".")),
      }))
      .filter((l) => !Number.isNaN(l.quantity) && l.quantity > 0);
    if (!lines.length) {
      setError("Добавьте строку с позицией и количеством > 0");
      return;
    }
    setMovSubmitting(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        stock_location_id: movFormLocId,
        doc_kind: movKind,
        remark: movRemark.trim() || null,
        lines,
      };
      if (movKind === "goods_transfer") {
        payload.to_stock_location_id = movToLocId;
      }
      const r = await fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/movements`, {
        method: "POST",
        headers: { ...h, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      setMovRemark("");
      setMovRows([{ itemId: "", qty: "1" }]);
      await load();
      await loadBalances();
    } finally {
      setMovSubmitting(false);
    }
  };

  const handleImportBalanceCsv = async (file: File | null) => {
    if (!file || !currentClinicId || !balanceLocId) return;
    const h = authHeaders();
    if (!h) return;
    setImportBalanceBusy(true);
    setImportBalanceSummary(null);
    setError(null);
    try {
      const idempotencyKey =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch(
        `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/stock-locations/${balanceLocId}/balances/import-csv`,
        { method: "POST", headers: { ...h, "Idempotency-Key": idempotencyKey }, body: fd },
      );
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      const j = (await r.json()) as {
        created: number;
        updated: number;
        skipped: number;
        errors: string[];
      };
      let msg = `Остатки: создано записей ${j.created}, обновлено ${j.updated}, пропущено ${j.skipped}.`;
      if (j.errors?.length) {
        msg += ` ${j.errors.slice(0, 5).join("; ")}`;
      }
      setImportBalanceSummary(msg);
      await loadBalances();
      await load();
    } finally {
      setImportBalanceBusy(false);
    }
  };

  const handleImportNomenclatureCsv = async (file: File | null) => {
    if (!file || !currentClinicId) return;
    const h = authHeaders();
    if (!h) return;
    setImportCsvBusy(true);
    setImportCsvSummary(null);
    setError(null);
    try {
      const idempotencyKey =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch(
        `${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/nomenclature/import-csv`,
        { method: "POST", headers: { ...h, "Idempotency-Key": idempotencyKey }, body: fd },
      );
      if (!r.ok) {
        setError((await parseJsonError(r)) ?? r.statusText);
        return;
      }
      const j = (await r.json()) as {
        created: number;
        updated: number;
        skipped: number;
        errors: string[];
      };
      let msg = `Импорт: создано ${j.created}, обновлено ${j.updated}, пропущено ${j.skipped}.`;
      if (j.errors?.length) {
        msg += ` Предупреждения: ${j.errors.slice(0, 5).join("; ")}`;
      }
      setImportCsvSummary(msg);
      await load();
      await loadBalances();
    } finally {
      setImportCsvBusy(false);
    }
  };

  const handleDeleteNom = async (id: string) => {
    if (!currentClinicId) return;
    const h = authHeaders();
    if (!h) return;
    setError(null);
    const r = await fetch(`${API_BASE}/v1/admin/clinics/${currentClinicId}/commerce/nomenclature/${id}`, {
      method: "DELETE",
      headers: h,
    });
    if (!r.ok) {
      setError((await parseJsonError(r)) ?? r.statusText);
      return;
    }
    await load();
    await loadBalances();
  };

  const entitlementDenied = error?.toLowerCase() === "entitlement_required";

  return (
    <Stack gap="md" p="md">
      <ContextBar
        title="Магазин (Commerce)"
        breadcrumbs={
          <Text size="sm" c="dimmed">
            Фаза 4 · опция commerce.store_network · отдельно от ERP-склада
          </Text>
        }
      />

      {!orgReady && (
        <Alert color="yellow" title="Нет организации">
          Привяжите администратора к организации SaaS, чтобы включить гейты опций.
        </Alert>
      )}

      {entitlementDenied && (
        <Alert color="red" title="Нет опции тарифа">
          Требуется entitlement <Code>commerce.store_network</Code> для организации.
        </Alert>
      )}

      {!entitlementDenied && error && (
        <Alert color="red" title="Ошибка">
          {error}
        </Alert>
      )}

      {!entitlementDenied && orgReady && currentClinicId && activeClinic && (
        <AdminSettingsSectionCard
          title="Витрина в приложении пациента (PWA)"
          description="Шаблон витрины как у простого онлайн-магазина: карточки активных позиций номенклатуры, без корзины и оплаты в этом релизе. Включите, когда готовы показывать ассортимент клиентам."
        >
          <Stack gap="sm">
            <Checkbox
              label="Показывать раздел «Магазин» в меню приложения пациента"
              checked={storeVisible}
              onChange={(e) => setStoreVisible(e.currentTarget.checked)}
            />
            <TextInput
              label="Заголовок раздела"
              placeholder="Например: Магазин клиники"
              value={storeTitle}
              onChange={(e) => setStoreTitle(e.currentTarget.value)}
              disabled={!storeVisible}
            />
            <Textarea
              label="Подзаголовок (опционально)"
              placeholder="Короткий текст под заголовком"
              value={storeSubtitle}
              onChange={(e) => setStoreSubtitle(e.currentTarget.value)}
              minRows={2}
              disabled={!storeVisible}
            />
            <Text size="xs" c="dimmed">
              Публичный каталог (без авторизации):{" "}
              <Code>
                {typeof window !== "undefined" ? window.location.origin : ""}
                /api/v1/public/clinics/{currentClinicId}/commerce/vitrine
              </Code>
            </Text>
            <Button
              size="sm"
              variant="filled"
              color="slate"
              loading={storeSaving}
              onClick={async () => {
                if (!currentClinicId) return;
                setStoreSaving(true);
                try {
                  await updateClinic.mutateAsync({
                    clinicId: currentClinicId,
                    body: {
                      patient_store_visible: storeVisible,
                      patient_store_title: storeTitle.trim() || null,
                      patient_store_subtitle: storeSubtitle.trim() || null,
                    },
                  });
                } finally {
                  setStoreSaving(false);
                }
              }}
            >
              Сохранить настройки витрины
            </Button>
          </Stack>
        </AdminSettingsSectionCard>
      )}

      <AdminSettingsSectionCard title="Сводка" description="Точки продаж и номенклатура (ADR-013).">
        {loading && <Text size="sm">Загрузка…</Text>}
        {!loading && overview && (
          <Stack gap="xs">
            <Text size="sm">
              Точки (stock locations): <strong>{overview.stock_locations_count}</strong>
            </Text>
            <Text size="sm">
              Позиции номенклатуры: <strong>{overview.nomenclature_items_count}</strong>
            </Text>
          </Stack>
        )}
        <Group mt="md">
          <Button
            variant="light"
            size="xs"
            onClick={() => {
              void load();
              void loadBalances();
            }}
            disabled={loading}
          >
            Обновить
          </Button>
        </Group>
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="Журнал импортов CSV"
        description="Аудит загрузок (4-F5). Каждая загрузка из UI отправляет свой Idempotency-Key; повтор с тем же ключом и тем же профилем не дублирует данные после успешного импорта."
      >
        {loading && <Text size="sm">Загрузка…</Text>}
        {!loading && importJobs.length === 0 && (
          <Text size="sm" c="dimmed">
            Импортов ещё не было.
          </Text>
        )}
        {!loading && importJobs.length > 0 && (
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Время</Table.Th>
                <Table.Th>Профиль</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Файл</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {importJobs.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>{new Date(row.created_at).toLocaleString()}</Table.Td>
                  <Table.Td>
                    <Code>{row.source_profile}</Code>
                  </Table.Td>
                  <Table.Td>{row.status}</Table.Td>
                  <Table.Td>{row.file_name ?? "—"}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="Сеть организации"
        description="Read-model по всем клиникам организации: точки, номенклатура, суммарный остаток (4-F3)."
      >
        {loading && <Text size="sm">Загрузка…</Text>}
        {!loading && networkOverview && (
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              Итого по сети: точек <strong>{networkOverview.totals.stock_locations_total}</strong>, позиций
              номенклатуры <strong>{networkOverview.totals.nomenclature_items_total}</strong>, на руках{" "}
              <strong>{String(networkOverview.totals.total_on_hand_quantity)}</strong>
            </Text>
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Клиника</Table.Th>
                  <Table.Th>Точки</Table.Th>
                  <Table.Th>Номенклатура</Table.Th>
                  <Table.Th>Остаток (сумма)</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {networkOverview.clinics.map((row) => (
                  <Table.Tr key={row.clinic_id}>
                    <Table.Td>{row.clinic_name}</Table.Td>
                    <Table.Td>{row.stock_locations_count}</Table.Td>
                    <Table.Td>{row.nomenclature_items_count}</Table.Td>
                    <Table.Td>{String(row.total_on_hand_quantity)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        )}
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="Точки продаж / склады"
        description="В рамках клиники; одна может быть «основной» для UX и остатков."
      >
        <Table striped highlightOnHover withTableBorder mb="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Код</Table.Th>
              <Table.Th>По умолчанию</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {locations.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>{row.name}</Table.Td>
                <Table.Td>{row.code ?? "—"}</Table.Td>
                <Table.Td>{row.is_default ? "Да" : "Нет"}</Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    {!row.is_default && (
                      <Button size="xs" variant="light" onClick={() => void handleSetDefaultLoc(row.id)}>
                        Основная
                      </Button>
                    )}
                    <Button size="xs" color="red" variant="subtle" onClick={() => void handleDeleteLoc(row.id)}>
                      Удалить
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        <Stack gap="sm">
          <TextInput label="Название точки" value={locName} onChange={(e) => setLocName(e.currentTarget.value)} />
          <TextInput label="Код (необязательно)" value={locCode} onChange={(e) => setLocCode(e.currentTarget.value)} />
          <Checkbox
            label="Сделать основной точкой"
            checked={locDefault}
            onChange={(e) => setLocDefault(e.currentTarget.checked)}
          />
          <Button onClick={() => void handleCreateLoc()} loading={locSubmitting} disabled={!locName.trim() || !orgReady}>
            Добавить точку
          </Button>
        </Stack>
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="Остатки по точке"
        description="Количество по каждой позиции на точке; также меняется документами прихода/расхода."
      >
        {!locations.length ? (
          <Text size="sm" c="dimmed">
            Добавьте хотя бы одну точку продаж, чтобы вести остатки.
          </Text>
        ) : (
          <Stack gap="sm">
            <Select
              label="Точка"
              data={locations.map((l) => ({ value: l.id, label: l.name }))}
              value={balanceLocId}
              onChange={(v) => setBalanceLocId(v)}
              disabled={!orgReady}
            />
            <Text size="sm" c="dimmed">
              Импорт остатков CSV (профиль <Code>commerce_stock_balances_csv_v1</Code>): колонки{" "}
              <Code>sku</Code>, <Code>quantity</Code> для выбранной точки. Спецификация:{" "}
              <Code>
                {"/v1/admin/clinics/{clinic_id}/commerce/stock-locations/{location_id}/balances/import-spec"}
              </Code>
            </Text>
            <FileInput
              label="Загрузить остатки (CSV)"
              placeholder="Выберите файл"
              accept=".csv,text/csv"
              clearable
              disabled={!orgReady || !balanceLocId || importBalanceBusy}
              onChange={(f) => void handleImportBalanceCsv(f)}
            />
            {importBalanceSummary && (
              <Text size="sm" c="dimmed">
                {importBalanceSummary}
              </Text>
            )}
            {balanceLoading && <Text size="sm">Загрузка остатков…</Text>}
            {!balanceLoading && balanceLines.length === 0 && (
              <Text size="sm" c="dimmed">
                Нет позиций номенклатуры — создайте их ниже.
              </Text>
            )}
            {!balanceLoading && balanceLines.length > 0 && (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Позиция</Table.Th>
                    <Table.Th>SKU</Table.Th>
                    <Table.Th>Количество</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {balanceLines.map((row) => (
                    <Table.Tr key={row.nomenclature_item_id}>
                      <Table.Td>
                        {row.name} ({row.unit})
                      </Table.Td>
                      <Table.Td>{row.sku ?? "—"}</Table.Td>
                      <Table.Td w={160}>
                        <NumberInput
                          size="xs"
                          min={0}
                          decimalScale={4}
                          value={pendingQty[row.nomenclature_item_id] ?? ""}
                          onChange={(v) =>
                            setPendingQty((p) => ({
                              ...p,
                              [row.nomenclature_item_id]: v === "" ? "" : String(v),
                            }))
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <Button
                          size="xs"
                          loading={savingBalanceItemId === row.nomenclature_item_id}
                          onClick={() => void handleSaveBalanceRow(row.nomenclature_item_id)}
                        >
                          Сохранить
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Stack>
        )}
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard
        title="Документы движения"
        description="Приход и расход по одной точке; перемещение (goods_transfer) списывает с «откуда» и приходует на «куда». Нехватка на расходе/перемещении — отказ."
      >
        <Table striped highlightOnHover withTableBorder mb="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Дата</Table.Th>
              <Table.Th>Тип</Table.Th>
              <Table.Th>Точка / маршрут</Table.Th>
              <Table.Th>Комментарий</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {movements.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>{new Date(row.created_at).toLocaleString()}</Table.Td>
                <Table.Td>
                  {row.doc_kind === "goods_out"
                    ? "Расход"
                    : row.doc_kind === "goods_transfer"
                      ? "Перемещение"
                      : "Приход"}
                </Table.Td>
                <Table.Td>
                  {row.doc_kind === "goods_transfer" && row.to_stock_location_id
                    ? `${locations.find((l) => l.id === row.stock_location_id)?.name ?? "?"} → ${locations.find((l) => l.id === row.to_stock_location_id)?.name ?? "?"}`
                    : (locations.find((l) => l.id === row.stock_location_id)?.name ?? row.stock_location_id)}
                </Table.Td>
                <Table.Td>{row.remark ?? "—"}</Table.Td>
                <Table.Td>
                  <Button size="xs" variant="light" onClick={() => void openMovementDetail(row.id)}>
                    Строки
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {!locations.length ? (
          <Text size="sm" c="dimmed">
            Нужна точка продаж и номенклатура для проведения документа.
          </Text>
        ) : (
          <Stack gap="sm">
            <Select
              label={movKind === "goods_transfer" ? "Откуда" : "Точка для документа"}
              data={locations.map((l) => ({ value: l.id, label: l.name }))}
              value={movFormLocId}
              onChange={(v) => setMovFormLocId(v)}
              disabled={!orgReady}
            />
            {movKind === "goods_transfer" && (
              <Select
                label="Куда"
                data={locations
                  .filter((l) => l.id !== movFormLocId)
                  .map((l) => ({ value: l.id, label: l.name }))}
                value={movToLocId}
                onChange={(v) => setMovToLocId(v)}
                disabled={!orgReady || locations.length < 2}
              />
            )}
            {movKind === "goods_transfer" && locations.length < 2 && (
              <Text size="sm" c="dimmed">
                Создайте вторую точку, чтобы проводить перемещения.
              </Text>
            )}
            <Select
              label="Тип"
              data={[
                { value: "goods_in", label: "Приход" },
                { value: "goods_out", label: "Расход" },
                { value: "goods_transfer", label: "Перемещение" },
              ]}
              value={movKind}
              onChange={(v) =>
                setMovKind((v as "goods_in" | "goods_out" | "goods_transfer") ?? "goods_in")
              }
            />
            <Textarea
              label="Комментарий (необязательно)"
              value={movRemark}
              onChange={(e) => setMovRemark(e.currentTarget.value)}
              minRows={2}
            />
            {movRows.map((mr, idx) => (
              <Group key={idx} align="flex-end" wrap="nowrap">
                <Select
                  label={idx === 0 ? "Позиция" : undefined}
                  placeholder="Номенклатура"
                  data={nomenclature
                    .filter((n) => n.is_active)
                    .map((n) => ({
                      value: n.id,
                      label: `${n.name}${n.sku ? ` (${n.sku})` : ""}`,
                    }))}
                  value={mr.itemId || null}
                  onChange={(v) =>
                    setMovRows((rows) => rows.map((x, i) => (i === idx ? { ...x, itemId: v ?? "" } : x)))
                  }
                  searchable
                  style={{ flex: 1 }}
                />
                <NumberInput
                  label={idx === 0 ? "Кол-во" : undefined}
                  min={0.0001}
                  decimalScale={4}
                  value={mr.qty}
                  onChange={(v) =>
                    setMovRows((rows) => rows.map((x, i) => (i === idx ? { ...x, qty: v === "" ? "" : String(v) } : x)))
                  }
                  w={140}
                />
                {movRows.length > 1 && (
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    onClick={() => setMovRows((rows) => rows.filter((_, i) => i !== idx))}
                  >
                    Убрать
                  </Button>
                )}
              </Group>
            ))}
            <Group>
              <Button
                size="xs"
                variant="light"
                onClick={() => setMovRows((rows) => [...rows, { itemId: "", qty: "1" }])}
              >
                Добавить строку
              </Button>
            </Group>
            <Button
              onClick={() => void handlePostMovement()}
              loading={movSubmitting}
              disabled={
                !orgReady ||
                (movKind === "goods_transfer" &&
                  (locations.length < 2 || !movToLocId || movToLocId === movFormLocId))
              }
            >
              Провести документ
            </Button>
          </Stack>
        )}
      </AdminSettingsSectionCard>

      <AdminSettingsSectionCard title="Номенклатура" description="SKU в контексте Commerce (не путать с ERP products).">
        {nomenclature.some((r) => r.is_active) ? (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md" mb="lg">
            {nomenclature
              .filter((r) => r.is_active)
              .map((row) => (
                <Paper key={row.id} withBorder radius="md" p="md" shadow="xs">
                  <Group align="flex-start" wrap="nowrap" gap="sm">
                    <ThemeIcon size={44} radius="md" variant="light" color="slate">
                      <IconShoppingBag size={22} stroke={1.25} />
                    </ThemeIcon>
                    <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                      <Text fw={700} size="sm" lineClamp={2}>
                        {row.name}
                      </Text>
                      <Group gap={6}>
                        {row.sku ? (
                          <Badge size="xs" variant="light" color="gray">
                            {row.sku}
                          </Badge>
                        ) : null}
                        <Badge size="xs" variant="outline" color="gray">
                          {row.unit}
                        </Badge>
                      </Group>
                    </Stack>
                  </Group>
                </Paper>
              ))}
          </SimpleGrid>
        ) : (
          <Text size="sm" c="dimmed" mb="md">
            Карточки появятся после создания активных позиций ниже или импорта CSV.
          </Text>
        )}
        <Stack gap="sm" mb="md">
          <Text size="sm" c="dimmed">
            Импорт CSV (профиль <Code>commerce_nomenclature_csv_v1</Code>): колонка <Code>name</Code> обязательна;
            опционально <Code>sku</Code> (сопоставление с существующими позициями), <Code>unit</Code>,{" "}
            <Code>is_active</Code>. Кодировка UTF-8. Машиночитаемая спецификация — GET{" "}
            <Code>{"/v1/admin/clinics/{clinic_id}/commerce/nomenclature/import-spec"}</Code>.
          </Text>
          <FileInput
            label="Загрузить CSV"
            placeholder="Выберите файл"
            accept=".csv,text/csv"
            clearable
            disabled={!orgReady || importCsvBusy}
            onChange={(f) => void handleImportNomenclatureCsv(f)}
          />
          {importCsvSummary && (
            <Text size="sm" c="dimmed">
              {importCsvSummary}
            </Text>
          )}
        </Stack>
        <Table striped highlightOnHover withTableBorder mb="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>SKU</Table.Th>
              <Table.Th>Ед.</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {nomenclature.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>{row.name}</Table.Td>
                <Table.Td>{row.sku ?? "—"}</Table.Td>
                <Table.Td>{row.unit}</Table.Td>
                <Table.Td>
                  <Badge size="sm" color={row.is_active ? "green" : "gray"} variant="light">
                    {row.is_active ? "Активна" : "Выкл."}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <Button size="xs" variant="light" onClick={() => void handleToggleNomActive(row)}>
                      {row.is_active ? "Деактивировать" : "Активировать"}
                    </Button>
                    <Button size="xs" variant="light" onClick={() => openEditNom(row)}>
                      Изменить
                    </Button>
                    <Button size="xs" color="red" variant="subtle" onClick={() => void handleDeleteNom(row.id)}>
                      Удалить
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        <Stack gap="sm">
          <TextInput label="Название" value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <TextInput label="SKU (необязательно)" value={sku} onChange={(e) => setSku(e.currentTarget.value)} />
          <Button onClick={() => void handleCreateNom()} loading={submitting} disabled={!name.trim() || !orgReady}>
            Создать позицию
          </Button>
        </Stack>
      </AdminSettingsSectionCard>

      <Modal
        opened={movModalOpen}
        onClose={() => {
          setMovModalOpen(false);
          setMovDetail(null);
        }}
        title="Документ движения"
        size="lg"
      >
        {movDetailLoading && <Text size="sm">Загрузка…</Text>}
        {!movDetailLoading && movDetail && (
          <Stack gap="sm">
            <Text size="sm">
              Тип:{" "}
              <strong>
                {movDetail.doc_kind === "goods_out"
                  ? "Расход"
                  : movDetail.doc_kind === "goods_transfer"
                    ? "Перемещение"
                    : "Приход"}
              </strong>
            </Text>
            <Text size="sm">
              {movDetail.doc_kind === "goods_transfer" && movDetail.to_stock_location_id ? (
                <>
                  Откуда:{" "}
                  {locations.find((l) => l.id === movDetail.stock_location_id)?.name ??
                    movDetail.stock_location_id}
                  <br />
                  Куда:{" "}
                  {locations.find((l) => l.id === movDetail.to_stock_location_id)?.name ??
                    movDetail.to_stock_location_id}
                </>
              ) : (
                <>
                  Точка:{" "}
                  {locations.find((l) => l.id === movDetail.stock_location_id)?.name ??
                    movDetail.stock_location_id}
                </>
              )}
            </Text>
            {movDetail.remark && (
              <Text size="sm">
                Комментарий: {movDetail.remark}
              </Text>
            )}
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Позиция</Table.Th>
                  <Table.Th>SKU</Table.Th>
                  <Table.Th>Кол-во</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {movDetail.lines.map((ln) => (
                  <Table.Tr key={ln.nomenclature_item_id}>
                    <Table.Td>
                      {ln.name} ({ln.unit})
                    </Table.Td>
                    <Table.Td>{ln.sku ?? "—"}</Table.Td>
                    <Table.Td>{String(ln.quantity)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        )}
      </Modal>

      <Modal
        opened={nomModalOpen}
        onClose={() => {
          setNomModalOpen(false);
          setEditNom(null);
        }}
        title="Редактирование позиции"
      >
        <Stack gap="sm">
          <TextInput label="Название" value={editNomName} onChange={(e) => setEditNomName(e.currentTarget.value)} />
          <TextInput label="SKU" value={editNomSku} onChange={(e) => setEditNomSku(e.currentTarget.value)} />
          <TextInput label="Единица" value={editNomUnit} onChange={(e) => setEditNomUnit(e.currentTarget.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setNomModalOpen(false)}>
              Отмена
            </Button>
            <Button loading={nomEditSubmitting} disabled={!editNomName.trim()} onClick={() => void handleSaveEditNom()}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
