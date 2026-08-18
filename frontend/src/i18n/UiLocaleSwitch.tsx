import { SegmentedControl } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useUiLocale, type UiLocale } from "./useUiLocale";

/**
 * Single locale control (instrument): EN/RU, size sm, equal segment min-width.
 * Place on staff login form column and admin header (A1). Do not fork.
 */
export function UiLocaleSwitch() {
  const { t } = useTranslation("common");
  const { locale, setLocale } = useUiLocale();

  return (
    <SegmentedControl
      size="sm"
      value={locale}
      onChange={(value) => setLocale(value as UiLocale)}
      aria-label={t("language")}
      data={[
        { value: "en", label: t("languageEn") },
        { value: "ru", label: t("languageRu") },
      ]}
      styles={{
        root: { flexShrink: 0 },
        label: { minWidth: 36 },
      }}
    />
  );
}
