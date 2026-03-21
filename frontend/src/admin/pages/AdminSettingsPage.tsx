import { Link } from "react-router-dom";
import { Anchor, Stack, Text } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { ROUTE_PATHS } from "@/routePaths";

const links = [
  { to: ROUTE_PATHS.admin.paymentGateway, label: "Касса" },
  { to: ROUTE_PATHS.admin.agreements, label: "Соглашения" },
  { to: ROUTE_PATHS.admin.channels, label: "Каналы уведомлений" },
  {
    to: ROUTE_PATHS.admin.omniChannels,
    label: "Омниканальные каналы связи",
  },
  { to: ROUTE_PATHS.admin.omniAiSettings, label: "AI омниканального ассистента" },
  { to: ROUTE_PATHS.admin.integrations, label: "Интеграции" },
  { to: ROUTE_PATHS.admin.styling, label: "Оформление" },
  { to: ROUTE_PATHS.admin.stickers, label: "Стикеры" },
  { to: ROUTE_PATHS.admin.notificationPolicy, label: "Политика уведомлений" },
  { to: ROUTE_PATHS.admin.clientReference, label: "Справка для клиента" },
];

export default function AdminSettingsPage() {
  return (
    <Stack gap="md">
      <ContextBar title="Настройки" />
      <Text size="sm" c="dimmed">
        Выберите раздел для настройки клиники.
      </Text>
      <Stack gap="xs">
        {links.map(({ to, label }) => (
          <Anchor key={to} component={Link} to={to} size="md">
            {label}
          </Anchor>
        ))}
      </Stack>
    </Stack>
  );
}
