import { API_BASE, newOutboundRequestId } from "@/api/client";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useClinics } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Badge, Box, Button, Group, Loader, Paper, SimpleGrid, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconShoppingCart } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";

const SELECTED_CLINIC_KEY = "app.selectedClinicId";

type VitrineItem = { id: string; name: string; sku: string | null; unit: string };

type VitrineResponse = {
  enabled: boolean;
  section_title: string | null;
  section_subtitle: string | null;
  items: VitrineItem[];
};

export default function StorePage() {
  const { accessToken } = usePatientAuth();
  const { data: clinics } = useClinics();
  const selectedClinicId =
    typeof localStorage !== "undefined" ? localStorage.getItem(SELECTED_CLINIC_KEY) : null;
  const clinic = useMemo(
    () => clinics?.find((c) => c.id === selectedClinicId) ?? clinics?.[0],
    [clinics, selectedClinicId],
  );

  const [data, setData] = useState<VitrineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!clinic?.id) {
      setLoading(false);
      setData(null);
      return;
    }
    if (!clinic.patient_store_visible) {
      setData({ enabled: false, section_title: null, section_subtitle: null, items: [] });
      setLoading(false);
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const r = await fetch(`${API_BASE}/v1/public/clinics/${clinic.id}/commerce/vitrine`, {
        headers: { "X-Trace-Id": newOutboundRequestId() },
      });
      if (r.status === 429) {
        setErr("Слишком много запросов. Подождите минуту и нажмите «Повторить».");
        setData(null);
        return;
      }
      if (!r.ok) {
        setErr("Не удалось загрузить витрину");
        setData(null);
        return;
      }
      setData((await r.json()) as VitrineResponse);
    } catch {
      setErr("Ошибка сети");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [clinic?.id, clinic?.patient_store_visible]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!accessToken) {
    return null;
  }

  if (!clinic) {
    return (
      <Stack p="md">
        <Text size="sm" c="dimmed">
          Выберите клинику в приложении.
        </Text>
      </Stack>
    );
  }

  if (!clinic.patient_store_visible) {
    return (
      <Stack p="md" gap="md">
        <Title order={2}>Магазин</Title>
        <EmptyStateHint
          title="Витрина не подключена"
          subtitle="Владелец клиники может включить магазин в админке: раздел «Магазин (Commerce)» — блок про приложение пациента."
        />
        <Text size="sm" c="dimmed" component={Link} to={ROUTE_PATHS.patient.chat}>
          Есть вопрос по товарам — напишите в чат клиники.
        </Text>
      </Stack>
    );
  }

  if (loading) {
    return (
      <Group justify="center" p="xl">
        <Loader />
      </Group>
    );
  }

  if (err) {
    return (
      <Stack p="md" gap="sm">
        <Text c="red">{err}</Text>
        <Button size="xs" variant="light" onClick={() => void load()}>
          Повторить
        </Button>
      </Stack>
    );
  }

  const title = data?.section_title?.trim() || "Магазин";
  const subtitle = data?.section_subtitle?.trim() || null;
  const items = data?.items ?? [];

  return (
    <Stack p="md" gap="lg">
      <div>
        <Title order={2}>{title}</Title>
        {subtitle ? (
          <Text size="sm" c="dimmed" mt={6}>
            {subtitle}
          </Text>
        ) : (
          <Text size="sm" c="dimmed" mt={6}>
            Ассортимент клиники. Оформление заказа и оплата в приложении появятся в следующих версиях — уточняйте
            наличие и цену в чате.
          </Text>
        )}
      </div>

      {items.length === 0 ? (
        <EmptyStateHint title="Пока нет позиций" subtitle="Администратор добавит товары в номенклатуре Commerce." />
      ) : (
        <SimpleGrid cols={{ base: 1, xs: 2, sm: 2 }} spacing="md">
          {items.map((it) => (
            <Paper
              key={it.id}
              withBorder
              radius="lg"
              p="md"
              shadow="xs"
              style={{ borderColor: "var(--mantine-color-gray-2)" }}
            >
              <Group align="flex-start" wrap="nowrap" gap="sm">
                <ThemeIcon size={48} radius="md" variant="light" color="slate">
                  <IconShoppingCart size={26} stroke={1.25} />
                </ThemeIcon>
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Text fw={700} size="sm" lineClamp={2}>
                    {it.name}
                  </Text>
                  <Group gap={6} mt={6}>
                    {it.sku ? (
                      <Badge size="xs" variant="light" color="gray">
                        {it.sku}
                      </Badge>
                    ) : null}
                    <Badge size="xs" variant="outline" color="gray">
                      {it.unit}
                    </Badge>
                  </Group>
                </Box>
              </Group>
            </Paper>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}
