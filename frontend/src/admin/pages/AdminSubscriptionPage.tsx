import { Stack, Text } from "@mantine/core";
import { PlatformPricingSection } from "@/marketing/components/PlatformPricingSection";
import { AdminSubscriptionCapabilitiesCard } from "@/admin/components/AdminSubscriptionCapabilitiesCard";
import { ContextBar } from "@/shared/ui/ContextBar";

/** Подписка SaaS: текущие entitlements + справочный каталог (без checkout — см. `PlatformPricingSection` mode). */
export default function AdminSubscriptionPage() {
  return (
    <Stack gap="lg">
      <ContextBar title="Подписка платформы" />
      <Text size="sm" c="dimmed">
        Здесь видно, какие опции включены для вашей организации, и актуальные цены с витрины. Онлайн-оплата
        с публичной страницы предназначена для новой регистрации клиники; апгрейд существующей организации —
        через оператора платформы до появления контура самообслуживания для владельца.
      </Text>
      <AdminSubscriptionCapabilitiesCard />
      <PlatformPricingSection mode="catalog_only" />
    </Stack>
  );
}
