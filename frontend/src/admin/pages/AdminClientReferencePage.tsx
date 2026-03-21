import {
  useAdminClientReference,
  useUpdateAdminClientReferenceMutation,
} from "@/hooks/useAdminClientReference";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { QueryErrorAlert } from "@/shared/ui";
import { Button, Paper, ScrollArea, Stack, Text, Textarea } from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { useState, useEffect } from "react";

export default function AdminClientReferencePage() {
  const { data, isLoading, isError, error } = useAdminClientReference();
  const [content, setContent] = useState(data?.content ?? "");

  useEffect(() => {
    if (data?.content !== undefined) setContent(data.content);
  }, [data?.content]);

  const saveMutation = useUpdateAdminClientReferenceMutation();

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Справка для клиента" />
        <DataSkeleton lines={8} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <ContextBar title="Справка для клиента" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <ContextBar title="Справка для клиента" />
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
