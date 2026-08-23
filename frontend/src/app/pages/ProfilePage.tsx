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
import { SEMANTIC } from "@/shared/semanticUi";
import { useTranslation } from "react-i18next";

export default function ProfilePage() {
  const { t } = useTranslation("patient");
  const { accessToken, logout } = usePatientAuth();
  const navigate = useNavigate();
  const { data: loyaltyMe } = usePatientLoyaltyMe(accessToken);

  const handleReferral = () => {
    if (navigator.share) {
      navigator
        .share({
          title: t("profile.shareTitle"),
          text: t("profile.shareText"),
          url: window.location.origin + ROUTE_PATHS.patient.home,
        })
        .catch(() => {});
    } else {
      navigator.clipboard?.writeText(window.location.origin + ROUTE_PATHS.patient.home);
    }
  };

  return (
    <Stack gap="lg">
      <Title order={3}>{t("profile.title")}</Title>

      {/* Digital Wallet (баланс кэшбэка, прогресс до VIP) */}
      {loyaltyMe?.wallet && (
        <Card withBorder padding="md" radius="md">
          <Group gap="xs" mb="xs">
            <IconWallet size={20} />
            <Text fw={600}>{t("profile.wallet")}</Text>
          </Group>
          <Text size="xl" fw={700}>
            {loyaltyMe.wallet.balance} {loyaltyMe.wallet.currency}
          </Text>
          <Text size="xs" c="dimmed">
            {t("profile.cashback")}
          </Text>
          <Button
            component={Link}
            to={ROUTE_PATHS.patient.loyalty}
            variant="light"
            color={SEMANTIC.action.confirm}
            size="sm"
            mt="sm"
          >
            {t("profile.passes")}
          </Button>
        </Card>
      )}

      {(!loyaltyMe?.wallet || loyaltyMe.subscriptions.length === 0) && (
        <Card withBorder padding="md" radius="md">
          <Text size="sm" c="dimmed" mb="sm">
            {t("profile.emptyWallet")}
          </Text>
          <Button
            component={Link}
            to={ROUTE_PATHS.patient.loyalty}
            variant="light"
            color={SEMANTIC.action.confirm}
            size="sm"
          >
            {t("profile.goLoyalty")}
          </Button>
        </Card>
      )}

      {/* Реферальная кнопка «Подарить другу 1000₽» (Web Share API) */}
      <Card withBorder padding="md" radius="md">
        <Group gap="xs" mb="xs">
          <IconGift size={20} />
          <Text fw={600}>{t("profile.giftTitle")}</Text>
        </Group>
        <Text size="sm" c="dimmed" mb="sm">
          {t("profile.giftLead")}
        </Text>
        <Button
          color={SEMANTIC.action.send}
          variant="light"
          onClick={handleReferral}
          leftSection={<IconGift size={16} />}
        >
          {t("profile.share")}
        </Button>
      </Card>

      <Button
        variant="subtle"
        color={SEMANTIC.action.danger}
        leftSection={<IconDoorExit size={18} />}
        onClick={() => {
          logout();
          navigate(ROUTE_PATHS.marketing.landing);
        }}
      >
        {t("logout")}
      </Button>
    </Stack>
  );
}
