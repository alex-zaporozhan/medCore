import { Anchor, Button, Card, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useClinics } from "@/hooks";
import { useState, useEffect } from "react";
import { useUtmTracking } from "@/shared/utmTracking";

const SELECTED_CLINIC_KEY = "app.selectedClinicId";

export default function HomePage() {
  const { data: clinics, isLoading, isError, error } = useClinics();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Capture UTM parameters and session identifier when user lands on the home page.
  useUtmTracking();

  useEffect(() => {
    const saved = localStorage.getItem(SELECTED_CLINIC_KEY);
    if (saved && clinics?.some((c) => c.id === saved)) setSelectedId(saved);
    else if (clinics?.length === 1) {
      setSelectedId(clinics[0].id);
      localStorage.setItem(SELECTED_CLINIC_KEY, clinics[0].id);
    }
  }, [clinics]);

  const selectClinic = (id: string) => {
    setSelectedId(id);
    localStorage.setItem(SELECTED_CLINIC_KEY, id);
  };

  const hasSingleClinic = clinics && clinics.length === 1;
  const hasMultipleClinics = clinics && clinics.length > 1;

  return (
    <Stack align="center" justify="center" h="100%" px="md">
      <Paper radius="lg" shadow="sm" p="xl" maw={520} w="100%">
        <Stack gap="md">
          <Title order={2}>Онлайн‑запись к врачу</Title>
          <Text size="sm" c="dimmed">
            Выберите удобное время приёма, не звоня в клинику. Вся история
            посещений и записи будут доступны в вашем личном кабинете.
          </Text>
          <Button component={Link} to="/app/booking" size="md">
            Записаться на приём
          </Button>
          <Anchor component={Link} to="/app/history">
            Смотреть историю посещений
          </Anchor>
          {isLoading && (
            <Text size="sm" c="dimmed">
              Загружаем клиники...
            </Text>
          )}
          {isError && (
            <Text size="sm" c="red">
              {error instanceof Error ? error.message : "Не удалось загрузить клиники"}
            </Text>
          )}
          {hasSingleClinic && (
            <Card shadow="sm" radius="md" withBorder mt="md">
              <Stack gap={4}>
                <Text fw={500}>Клиника</Text>
                <Text size="sm">{clinics![0].name}</Text>
                {clinics![0].address && (
                  <Text size="sm" c="dimmed">
                    {clinics![0].address}
                  </Text>
                )}
                <Group gap="md" mt="xs">
                  {clinics![0].phone && (
                    <Text size="sm" c="dimmed">
                      Телефон: {clinics![0].phone}
                    </Text>
                  )}
                  {clinics![0].email && (
                    <Text size="sm" c="dimmed">
                      Email: {clinics![0].email}
                    </Text>
                  )}
                </Group>
              </Stack>
            </Card>
          )}
          {hasMultipleClinics && (
            <Stack gap="xs" mt="md">
              <Text size="sm" fw={500}>
                Выберите клинику перед записью
              </Text>
              {clinics!.map((c) => {
                const isSelected = selectedId === c.id;
                return (
                  <Card
                    key={c.id}
                    shadow="xs"
                    radius="md"
                    withBorder
                    style={{
                      cursor: "pointer",
                      borderWidth: isSelected ? 2 : 1,
                      borderColor: isSelected ? "var(--mantine-color-primary-6)" : undefined,
                      backgroundColor: isSelected ? "var(--mantine-color-primary-light)" : undefined,
                    }}
                    onClick={() => selectClinic(c.id)}
                  >
                    <Stack gap={4}>
                      <Text fw={500}>{c.name}</Text>
                      {c.address && (
                        <Text size="sm" c="dimmed">
                          {c.address}
                        </Text>
                      )}
                      <Group gap="md" mt="xs">
                        {c.phone && (
                          <Text size="sm" c="dimmed">
                            Телефон: {c.phone}
                          </Text>
                        )}
                        {c.email && (
                          <Text size="sm" c="dimmed">
                            Email: {c.email}
                          </Text>
                        )}
                      </Group>
                    </Stack>
                  </Card>
                );
              })}
            </Stack>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
