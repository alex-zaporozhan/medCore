import { Select, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useAdminClinic } from "@/contexts/AdminClinicContext";

type ClinicSelectorProps = {
  /** "field" — полноразмерный Select; "compact" — узкий для ContextBar */
  variant?: "field" | "compact";
};

/**
 * Единый выбор клиники для админки: при привязке к JWT показывается только доступная клиника.
 */
export function ClinicSelector({ variant = "field" }: ClinicSelectorProps) {
  const { t } = useTranslation("common");
  const {
    selectableClinics,
    currentClinicId,
    setCurrentClinicId,
    isClinicScopeLocked,
    isLoading,
  } = useAdminClinic();

  const options = selectableClinics.map((c) => ({
    value: c.id,
    label: c.name,
  }));

  if (isLoading) {
    return (
      <Text size="sm" c="dimmed">
        {t("clinics.loading")}
      </Text>
    );
  }

  if (variant === "compact") {
    return (
      <Select
        size="xs"
        data={options}
        value={currentClinicId}
        onChange={setCurrentClinicId}
        placeholder={options.length ? undefined : t("clinics.empty")}
        disabled={isClinicScopeLocked && options.length <= 1}
        title={isClinicScopeLocked ? t("clinics.jwtLockedTitleShort") : undefined}
        w={220}
        comboboxProps={{ withinPortal: true }}
      />
    );
  }

  return (
    <Select
      label={t("clinics.label")}
      data={options}
      value={currentClinicId}
      onChange={setCurrentClinicId}
      disabled={isClinicScopeLocked && options.length <= 1}
      description={isClinicScopeLocked ? t("clinics.jwtLockedDescription") : undefined}
    />
  );
}
