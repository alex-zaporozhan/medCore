/**
 * PWA 2.0: Профиль — Digital Wallet, реферальная кнопка, выход.
 */

import { useNavigate } from "react-router-dom";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { usePatientLoyaltyMe } from "@/hooks";
import { Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import { IconGift, IconWallet, IconDoorExit } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";

export default function ProfilePage() {
  const { accessToken, logout } = usePatientAuth();
  const navigate = useNavigate();
  const { data: loyaltyMe } = usePatientLoyaltyMe(accessToken);

  const handleReferral = () => {
    if (navigator.share) {
      navigator
        .share({
          title: "Dental Booking",
          text: "Подари другу 1000₽ — запишись по моей ссылке!",
          url: window.location.origin + ROUTE_PATHS.patient.home,
        })
        .catch(() => {});
    } else {
      navigator.clipboard?.writeText(window.location.origin + ROUTE_PATHS.patient.home);
    }
  };

  return (
    <Stack gap="lg">
      <Title order={3}>Профиль</Title>

      {/* Digital Wallet (баланс кэшбэка, прогресс до VIP) */}
      {loyaltyMe?.wallet && (
        <Card withBorder padding="md" radius="md">
          <Group gap="xs" mb="xs">
            <IconWallet size={20} />
            <Text fw={600}>Кошелёк</Text>
          </Group>
          <Text size="xl" fw={700}>
            {loyaltyMe.wallet.balance} {loyaltyMe.wallet.currency}
          </Text>
          <Text size="xs" c="dimmed">
            Кэшбэк с визитов. Можно списать при записи.
          </Text>
          <Button
            component={Link}
            to={ROUTE_PATHS.patient.loyalty}
            variant="light"
            color="indigo"
            size="sm"
            mt="sm"
          >
            Абонементы и баллы
          </Button>
        </Card>
      )}

      {(!loyaltyMe?.wallet || loyaltyMe.subscriptions.length === 0) && (
        <Card withBorder padding="md" radius="md">
          <Text size="sm" c="dimmed" mb="sm">
            Баланс и абонементы появятся после визитов.
          </Text>
          <Button
            component={Link}
            to={ROUTE_PATHS.patient.loyalty}
            variant="light"
            color="indigo"
            size="sm"
          >
            Перейти в раздел лояльности
          </Button>
        </Card>
      )}

      {/* Реферальная кнопка «Подарить другу 1000₽» (Web Share API) */}
      <Card withBorder padding="md" radius="md">
        <Group gap="xs" mb="xs">
          <IconGift size={20} />
          <Text fw={600}>Подарить другу 1000₽</Text>
        </Group>
        <Text size="sm" c="dimmed" mb="sm">
          Поделитесь ссылкой — друг получит бонус при записи.
        </Text>
        <Button color="indigo" onClick={handleReferral} leftSection={<IconGift size={16} />}>
          Поделиться ссылкой
        </Button>
      </Card>

      <Button
        variant="subtle"
        color="red"
        leftSection={<IconDoorExit size={18} />}
        onClick={() => {
          logout();
          navigate(ROUTE_PATHS.marketing.landing);
        }}
      >
        Выйти
      </Button>
    </Stack>
  );
}
