import { Link } from "react-router-dom";
import { Anchor, Stack, Text } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { ROUTE_PATHS } from "@/routePaths";

/** Единая точка входа: пункты убраны из бокового меню, чтобы не дублировать «Настройки» (`MASTER` §4). */
const links = [
  { to: ROUTE_PATHS.admin.paymentGateway, label: "Касса / платёжный шлюз" },
  { to: ROUTE_PATHS.admin.agreements, label: "Соглашения" },
  { to: ROUTE_PATHS.admin.channels, label: "Каналы уведомлений (SMS, Telegram, Email)" },
  { to: ROUTE_PATHS.admin.omniChannels, label: "Омниканальные каналы связи" },
  { to: ROUTE_PATHS.admin.omniAiSettings, label: "AI омниканального ассистента" },
  { to: ROUTE_PATHS.admin.integrations, label: "Интеграции (в т.ч. 1С)" },
  { to: ROUTE_PATHS.admin.styling, label: "Оформление приложения для пациента" },
  { to: ROUTE_PATHS.admin.stickers, label: "Стикеры" },
  { to: ROUTE_PATHS.admin.notificationPolicy, label: "Политика уведомлений" },
  { to: ROUTE_PATHS.admin.clientReference, label: "Справочник для клиента" },
  { to: ROUTE_PATHS.admin.discounts, label: "Скидки и акции" },
  { to: ROUTE_PATHS.admin.forms, label: "Цифровые формы" },
  { to: ROUTE_PATHS.admin.omniVault, label: "Omni-Vault" },
];

export default function AdminSettingsPage() {
  return (
    <Stack gap="md">
      <ContextBar title="Настройки" />
      <Text size="sm" c="dimmed">
        Все разделы конфигурации клиники — одна точка входа. Маршруты не изменились; из левого меню дубли убраны.
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
