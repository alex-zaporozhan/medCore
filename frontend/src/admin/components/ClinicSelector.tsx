import { Select, Text } from "@mantine/core";
import { useAdminClinic } from "@/contexts/AdminClinicContext";

type ClinicSelectorProps = {
  /** "field" — полноразмерный Select; "compact" — узкий для ContextBar */
  variant?: "field" | "compact";
};

/**
 * Единый выбор клиники для админки: при привязке к JWT показывается только доступная клиника.
 */
export function ClinicSelector({ variant = "field" }: ClinicSelectorProps) {
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
        Загрузка клиник…
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
        placeholder={options.length ? undefined : "Нет клиник"}
        disabled={isClinicScopeLocked && options.length <= 1}
        title={
          isClinicScopeLocked
            ? "Клиника совпадает с учётной записью (JWT)"
            : undefined
        }
        w={220}
        comboboxProps={{ withinPortal: true }}
      />
    );
  }

  return (
    <Select
      label="Клиника"
      data={options}
      value={currentClinicId}
      onChange={setCurrentClinicId}
      disabled={isClinicScopeLocked && options.length <= 1}
      description={
        isClinicScopeLocked
          ? "Совпадает с вашей учётной записью. Смена филиала — отдельный вход/роль."
          : undefined
      }
    />
  );
}
