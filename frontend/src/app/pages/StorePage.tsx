import { API_BASE, newOutboundRequestId } from "@/api/client";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useClinics } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Badge, Box, Button, Group, Loader, Paper, SimpleGrid, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconShoppingCart } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { useTranslation } from "react-i18next";

const SELECTED_CLINIC_KEY = "app.selectedClinicId";

type VitrineItem = { id: string; name: string; sku: string | null; unit: string };

type VitrineResponse = {
  enabled: boolean;
  section_title: string | null;
  section_subtitle: string | null;
  items: VitrineItem[];
};

export default function StorePage() {
  const { t } = useTranslation("patient");
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
        setErr(t("store.rateLimit"));
        setData(null);
        return;
      }
      if (!r.ok) {
        setErr(t("store.loadFailed"));
        setData(null);
        return;
      }
      setData((await r.json()) as VitrineResponse);
    } catch {
      setErr(t("store.network"));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [clinic?.id, clinic?.patient_store_visible, t]);

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
          {t("store.pickClinic")}
        </Text>
      </Stack>
    );
  }

  if (!clinic.patient_store_visible) {
    return (
      <Stack p="md" gap="md">
        <Title order={2}>{t("store.title")}</Title>
        <EmptyStateHint
          title={t("store.offTitle")}
          subtitle={t("store.offHint")}
        />
        <Text size="sm" c="dimmed" component={Link} to={ROUTE_PATHS.patient.chat}>
          {t("store.askChat")}
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
          {t("store.retry")}
        </Button>
      </Stack>
    );
  }

  const title = data?.section_title?.trim() || t("store.title");
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
            {t("store.lead")}
          </Text>
        )}
      </div>

      {items.length === 0 ? (
        <EmptyStateHint title={t("store.emptyTitle")} subtitle={t("store.emptyHint")} />
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
