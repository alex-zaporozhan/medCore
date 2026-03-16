import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useClinics } from "@/hooks";
import { api } from "@/api/client";
import { useQueryClient } from "@tanstack/react-query";
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
  const qc = useQueryClient();
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
      await api.put(`/v1/clinics/${currentClinicId}`, {
        theme_primary_color: primaryColor.trim() || null,
        theme_logo_url: logoUrl.trim() || null,
        theme_font_family: fontFamily.trim() || null,
      });
      qc.invalidateQueries({ queryKey: ["clinics"] });
      await refetch();
    } finally {
      setSaving(false);
    }
  };

  const paletteRef = [
    { name: "Фон страницы", var: "--bg-main", hex: "#F8FAFB" },
    { name: "Карточка", var: "--bg-card", hex: "#FFFFFF" },
    { name: "Боковая панель", var: "--bg-sidebar", hex: "#F1F4F6" },
    { name: "Акцент (основной)", var: "--primary", hex: "#9CB4C4" },
    { name: "Акцент hover", var: "--primary-hover", hex: "#8AA3B5" },
    { name: "Акцент active", var: "--primary-active", hex: "#7A92A3" },
    { name: "Акцент светлый", var: "--primary-light", hex: "#EBF1F4" },
    { name: "Граница полей", var: "--input-border", hex: "#DDE4E9" },
    { name: "Разделитель", var: "--divider", hex: "#EEF2F4" },
    { name: "Основной текст", var: "--text-main", hex: "#3E4954" },
    { name: "Вспом. текст", var: "--text-muted", hex: "#86929D" },
    { name: "Успех", var: "--success", hex: "#92B191" },
    { name: "Золотой акцент", var: "--accent-gold", hex: "#D4AF37" },
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
            placeholder="#9CB4C4"
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
