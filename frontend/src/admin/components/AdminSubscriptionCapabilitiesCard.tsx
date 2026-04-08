import { Anchor, Badge, Group, Paper, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconCircleCheck, IconCircleMinus, IconReceipt } from "@tabler/icons-react";
import { Link, useLocation } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { useAdminSession } from "@/hooks/useAdminSession";
import { COMMERCIAL_ENTITLEMENT_KEYS, labelForEntitlementKey } from "@/shared/entitlementDisplay";

/**
 * Карточка «Подписка и возможности»: связывает SaaS-тариф (entitlements) с ожиданиями Владельца.
 * RBAC по-прежнему ограничивает действия; эта карточка про «что куплено у платформы».
 */
export function AdminSubscriptionCapabilitiesCard() {
  const location = useLocation();
  const { data: session, isLoading } = useAdminSession();
  const orgId = session?.organization_id;
  const enforced = session?.entitlement_enforced ?? false;
  const keys = session?.entitlement_keys ?? [];
  const isOwner = session?.roles?.includes("owner") ?? false;

  if (isLoading || !session) return null;

  if (!orgId) {
    return (
      <Paper p="lg" radius="md" withBorder shadow="xs">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Stack gap={4}>
            <Text fw={600} size="sm">
              Организация и подписка
            </Text>
            <Text size="sm" c="dimmed">
              Клиника без привязки к организации платформы: ограничения тарифа SaaS здесь не
              отображаются.
            </Text>
          </Stack>
        </Group>
      </Paper>
    );
  }

  const keySet = new Set(keys);
  const missingCommercial = enforced
    ? COMMERCIAL_ENTITLEMENT_KEYS.filter((k) => !keySet.has(k))
    : [];

  const activeExtras = keys.filter((k) => k !== "core.base");

  return (
    <Paper p="lg" radius="md" withBorder shadow="xs">
      <Group justify="space-between" align="flex-start" wrap="wrap" gap="md">
        <Group gap="sm" align="flex-start" wrap="nowrap">
          <ThemeIcon size={44} radius="md" variant="light" color="brand">
            <IconReceipt size={24} stroke={1.5} />
          </ThemeIcon>
          <Stack gap={6}>
            <Text fw={600}>Подписка и возможности платформы</Text>
            <Text size="sm" c="dimmed" maw={560}>
              {enforced
                ? "Разделы админки, относящиеся к опциям вне вашего тарифа, скрыты. Доступ сотрудников по-прежнему настраивается в «Права и политики»."
                : "Режим совместимости: ограничения по опциям тарифа не применяются (коробка или организация без записей entitlements). Контроль — через роли и права."}
            </Text>
          </Stack>
        </Group>
        {isOwner && location.pathname !== ROUTE_PATHS.admin.subscription ? (
          <Anchor component={Link} to={ROUTE_PATHS.admin.subscription} size="sm" fw={500}>
            Подписка и каталог →
          </Anchor>
        ) : null}
      </Group>

      <Stack gap="sm" mt="md">
        <Text size="xs" tt="uppercase" fw={700} c="dimmed">
          Включённые опции
        </Text>
        <Group gap="xs">
          {keySet.has("core.base") && (
            <Badge
              size="md"
              variant="light"
              color="teal"
              leftSection={<IconCircleCheck size={14} />}
            >
              {labelForEntitlementKey("core.base").title}
            </Badge>
          )}
          {activeExtras.map((k) => {
            const { title } = labelForEntitlementKey(k);
            return (
              <Badge
                key={k}
                size="md"
                variant="light"
                color="brand"
                leftSection={<IconCircleCheck size={14} />}
              >
                {title}
              </Badge>
            );
          })}
          {!keySet.has("core.base") && activeExtras.length === 0 && (
            <Text size="sm" c="dimmed">
              Нет распознанных ключей в сессии — проверьте провижининг организации.
            </Text>
          )}
        </Group>

        {enforced && missingCommercial.length > 0 && (
          <>
            <Text size="xs" tt="uppercase" fw={700} c="dimmed" mt="xs">
              Не входят в текущий тариф
            </Text>
            <Group gap="xs">
              {missingCommercial.map((k) => {
                const { title } = labelForEntitlementKey(k);
                return (
                  <Badge
                    key={k}
                    size="md"
                    variant="outline"
                    color="gray"
                    leftSection={<IconCircleMinus size={14} />}
                  >
                    {title}
                  </Badge>
                );
              })}
            </Group>
            {isOwner && (
              <Text size="sm" c="dimmed">
                Чтобы расширить набор, оформите апгрейд у платформы (каталог и контакты — на странице
                тарифов).
              </Text>
            )}
          </>
        )}
      </Stack>
    </Paper>
  );
}
