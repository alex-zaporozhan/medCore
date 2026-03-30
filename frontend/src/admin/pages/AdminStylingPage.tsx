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
    { name: "Фон страницы", var: "--bg-main", hex: "#F4F6F8" },
    { name: "Карточка", var: "--bg-card", hex: "#FFFFFF" },
    { name: "Боковая панель (пациент)", var: "--bg-sidebar", hex: "#FFFFFF" },
    { name: "Админ-сайдбар", var: "--admin-sidebar-bg", hex: "#FFFFFF" },
    { name: "Акцент (основной)", var: "--primary", hex: "#1C2E45" },
    { name: "Акцент hover", var: "--primary-hover", hex: "#152338" },
    { name: "Акцент active", var: "--primary-active", hex: "#0F1A28" },
    { name: "Акцент светлый", var: "--primary-light", hex: "#E8EEF3" },
    { name: "Граница полей", var: "--input-border", hex: "#E2E6EA" },
    { name: "Разделитель", var: "--divider", hex: "#E2E6EA" },
    { name: "Основной текст", var: "--text-main", hex: "#0F1419" },
    { name: "Вспом. текст", var: "--text-muted", hex: "#5C6D7A" },
    { name: "Успех", var: "--success", hex: "#065F46" },
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
            placeholder="#1C2E45"
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
