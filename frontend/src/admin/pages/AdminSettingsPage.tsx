import { Link } from "react-router-dom";
import { Anchor, Stack, Text } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";

const links = [
  { to: "/admin/payment-gateway", label: "Касса" },
  { to: "/admin/agreements", label: "Соглашения" },
  { to: "/admin/channels", label: "Каналы уведомлений" },
  {
    to: "/admin/omni-channels",
    label: "Омниканальные каналы связи",
  },
  { to: "/admin/omni-ai-settings", label: "AI омниканального ассистента" },
  { to: "/admin/integrations", label: "Интеграции" },
  { to: "/admin/styling", label: "Оформление" },
  { to: "/admin/stickers", label: "Стикеры" },
  { to: "/admin/notification-policy", label: "Политика уведомлений" },
  { to: "/admin/client-reference", label: "Справка для клиента" },
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
