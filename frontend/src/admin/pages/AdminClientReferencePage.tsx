import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { Button, Paper, ScrollArea, Stack, Text, Textarea, Title } from "@mantine/core";
import { useState, useEffect } from "react";

interface ClientReferenceResponse {
  content: string;
}

export default function AdminClientReferencePage() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["admin-client-reference"],
    queryFn: () => api.get<ClientReferenceResponse>("/v1/admin/client-reference"),
  });
  const [content, setContent] = useState(data?.content ?? "");

  useEffect(() => {
    if (data?.content !== undefined) setContent(data.content);
  }, [data?.content]);

  const saveMutation = useMutation({
    mutationFn: (body: { content: string }) =>
      api.put<ClientReferenceResponse>("/v1/admin/client-reference", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-client-reference"] });
    },
  });

  if (isLoading) {
    return (
      <Stack>
        <Title order={3}>Справка для клиента</Title>
        <DataSkeleton lines={8} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <Title order={3}>Справка для клиента</Title>
        <Text c="red">{error instanceof Error ? error.message : "Ошибка загрузки"}</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Title order={3}>Справка для клиента: возможные проблемы и сценарии</Title>
      <Text size="sm" c="dimmed">
        Документ для передачи заказчику. Можно редактировать и сохранять в систему. Поддерживается Markdown.
      </Text>
      <Paper p="md" radius="md" withBorder>
        <Stack gap="md">
          <ScrollArea h="60vh" type="scroll">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.currentTarget.value)}
              minRows={20}
              autosize
              styles={{ input: { fontFamily: "var(--mantine-font-family-mono)", fontSize: 13 } }}
              placeholder="Введите текст справки (Markdown)..."
            />
          </ScrollArea>
          <Button
            onClick={() => saveMutation.mutate({ content })}
            loading={saveMutation.isPending}
          >
            Сохранить
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
