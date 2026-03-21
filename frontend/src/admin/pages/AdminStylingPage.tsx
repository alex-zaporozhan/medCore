import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useClinics, useUpdateClinicMutation } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Card,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { useState, useEffect } from "react";

export default function AdminStylingPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: clinicsData, refetch } = useClinics();
  const updateClinic = useUpdateClinicMutation();
  const clinic = currentClinicId
    ? (clinicsData ?? []).find((c) => c.id === currentClinicId)
    : null;

  const [primaryColor, setPrimaryColor] = useState(clinic?.theme_primary_color ?? "");
  const [logoUrl, setLogoUrl] = useState(clinic?.theme_logo_url ?? "");
  const [fontFamily, setFontFamily] = useState(clinic?.theme_font_family ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (clinic) {
      setPrimaryColor(clinic.theme_primary_color ?? "");
      setLogoUrl(clinic.theme_logo_url ?? "");
      setFontFamily(clinic.theme_font_family ?? "");
    }
  }, [clinic?.id, clinic?.theme_primary_color, clinic?.theme_logo_url, clinic?.theme_font_family]);

  if (!currentClinicId) {
    return (
      <Stack>
        <ContextBar title="Оформление" />
        <EmptyStateHint title="Выберите клинику" />
      </Stack>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateClinic.mutateAsync({
        clinicId: currentClinicId,
        body: {
          theme_primary_color: primaryColor.trim() || null,
          theme_logo_url: logoUrl.trim() || null,
          theme_font_family: fontFamily.trim() || null,
        },
      });
      await refetch();
    } finally {
      setSaving(false);
    }
  };

  const paletteRef = [
    { name: "Фон страницы", var: "--bg-main", hex: "#F6F7FB" },
    { name: "Карточка", var: "--bg-card", hex: "#FFFFFF" },
    { name: "Боковая панель (пациент)", var: "--bg-sidebar", hex: "#EEF1F7" },
    { name: "Админ-сайдбар", var: "--admin-sidebar-bg", hex: "#F1F3F9" },
    { name: "Акцент (основной)", var: "--primary", hex: "#4F46E5" },
    { name: "Акцент hover", var: "--primary-hover", hex: "#4338CA" },
    { name: "Акцент active", var: "--primary-active", hex: "#3730A3" },
    { name: "Акцент светлый", var: "--primary-light", hex: "#EEF2FF" },
    { name: "Граница полей", var: "--input-border", hex: "#D5DBE8" },
    { name: "Разделитель", var: "--divider", hex: "#E4E8F0" },
    { name: "Основной текст", var: "--text-main", hex: "#334155" },
    { name: "Вспом. текст", var: "--text-muted", hex: "#64748B" },
    { name: "Успех", var: "--success", hex: "#15803D" },
    { name: "Золотой акцент", var: "--accent-gold", hex: "#B8860B" },
  ];

  return (
    <Stack>
      <ContextBar title="Оформление" />
      <Text size="sm" c="dimmed">
        Настройки применяются к приложению пациента: шапка, кнопки, карточки. Логотип показывается в шапке приложения вместо названия «Dental Booking». Один шрифт задаётся для всего приложения (заголовки и текст).
      </Text>
      <Card withBorder p="md" radius="md" style={{ maxWidth: 420 }}>
        <Stack gap="md">
          <TextInput
            label="Основной цвет (переменная --primary, hex или CSS)"
            placeholder="#4F46E5"
            value={primaryColor}
            onChange={(e) => setPrimaryColor(e.currentTarget.value)}
            description="Переопределяет цвет кнопок и шапки в приложении пациента"
          />
          <TextInput
            label="URL логотипа"
            placeholder="https://..."
            value={logoUrl}
            onChange={(e) => setLogoUrl(e.currentTarget.value)}
            description="Отображается в шапке приложения пациента"
          />
          <TextInput
            label="Шрифт (название или stack)"
            placeholder="Inter, sans-serif"
            value={fontFamily}
            onChange={(e) => setFontFamily(e.currentTarget.value)}
            description="Один шрифт для всего приложения пациента"
          />
          <Button onClick={handleSave} loading={saving}>
            Сохранить
          </Button>
        </Stack>
      </Card>
      <Card withBorder p="md" radius="md">
        <Text size="sm" fw={600} mb="xs">Палитра сайта (по техпаспорту)</Text>
        <Stack gap={4}>
          {paletteRef.map(({ name, var: v, hex }) => (
            <Text key={v} size="xs" c="dimmed" component="span" style={{ display: "flex", gap: 8 }}>
              <span style={{ width: 140 }}>{name}</span>
              <code style={{ fontFamily: "monospace" }}>{v}</code>
              <span style={{ color: hex, fontWeight: 600 }}>■</span>
              <span>{hex}</span>
            </Text>
          ))}
        </Stack>
      </Card>
    </Stack>
  );
}
