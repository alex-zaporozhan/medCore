import { Anchor, Group, Paper, Text } from "@mantine/core";
import { IconCoin } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ROUTE_PATHS } from "@/routePaths";
import { useAdminSession } from "@/hooks/useAdminSession";

/**
 * Компактная строка под шапкой контента для владельца: быстрый переход к экрану подписки.
 */
export function AdminOwnerSubscriptionStrip() {
  const { t } = useTranslation("common");
  const { data: session } = useAdminSession();
  const orgId = session?.organization_id;
  const isOwner = session?.roles?.includes("owner") ?? false;
  if (!orgId || !isOwner) return null;

  const enforced = session?.entitlement_enforced ?? false;
  const keys = session?.entitlement_keys ?? [];
  const summary = enforced
    ? t("subscription.tariffOptions", { count: keys.length })
    : t("subscription.unlimited");

  return (
    <Anchor
      component={Link}
      to={ROUTE_PATHS.admin.subscription}
      underline="never"
      display="block"
      mb="md"
    >
      <Paper
        p="sm"
        radius="md"
        withBorder
        shadow="none"
        style={{
          borderColor: "var(--mantine-color-brand-3)",
          background: "var(--mantine-color-brand-0)",
        }}
      >
        <Group justify="space-between" wrap="nowrap" gap="sm">
          <Group gap="xs" wrap="nowrap">
            <IconCoin size={20} stroke={1.5} color="var(--mantine-color-brand-7)" />
            <Text size="sm" fw={600} c="var(--text-main)">
              {summary}
            </Text>
          </Group>
          <Text size="xs" fw={600} c="brand" style={{ flexShrink: 0 }}>
            {t("subscription.cta")}
          </Text>
        </Group>
      </Paper>
    </Anchor>
  );
}
