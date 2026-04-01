import { Anchor, Box, Group, Image, Skeleton, Stack } from "@mantine/core";
import { useEffect, useState } from "react";
import { ChatInlineAudioPlayer } from "@/shared/ChatInlineAudioPlayer";

export type ClinicChatAttachmentBrief = {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes?: number;
};

function formatFileSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

type Props = {
  attachments: ClinicChatAttachmentBrief[];
  /** Загрузка байтов вложения (с авторизацией вызывающей стороны). */
  getBlob: (attachmentId: string) => Promise<Blob>;
  /**
   * Ссылка «скачать» и пункт загрузки в нативном плеере для audio/*.
   * По умолчанию false (пациент и админ без роли владельца).
   */
  allowAudioAttachmentDownload?: boolean;
};

function isAudioAttachment(ct: string): boolean {
  return ct.startsWith("audio/");
}

function isImageAttachment(ct: string): boolean {
  return ct.startsWith("image/");
}

/**
 * Превью изображений и кнопки скачивания для вложений любого чата с авторизованным `getBlob`
 * (пациентский чат, админский диалог, staff-chat и т.д.).
 */
export function ClinicChatAttachments({
  attachments,
  getBlob,
  allowAudioAttachmentDownload = false,
}: Props) {
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({});
  const attKey = attachments.map((a) => a.id).join(",");

  useEffect(() => {
    const created: string[] = [];
    let cancelled = false;
    const imgs = attachments.filter(
      (a) => a.content_type.startsWith("image/") || a.content_type.startsWith("audio/")
    );
    setImageUrls({});
    void (async () => {
      const next: Record<string, string> = {};
      for (const a of imgs) {
        try {
          const blob = await getBlob(a.id);
          if (cancelled) return;
          const u = URL.createObjectURL(blob);
          created.push(u);
          next[a.id] = u;
        } catch {
          /* ignore */
        }
      }
      if (!cancelled) setImageUrls(next);
    })();
    return () => {
      cancelled = true;
      created.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [attKey, attachments, getBlob]);

  if (!attachments.length) return null;

  return (
    <Stack gap="xs" mt={6}>
      {attachments.map((a) => {
        if (!a.content_type.startsWith("image/")) return null;
        if (!imageUrls[a.id]) {
          return (
            <Skeleton
              key={`img-sk-${a.id}`}
              height={160}
              radius="sm"
              maw={360}
              w="100%"
            />
          );
        }
        return (
          <Image
            key={a.id}
            src={imageUrls[a.id]}
            alt=""
            radius="sm"
            mah={200}
            w="auto"
            fit="contain"
          />
        );
      })}
      {attachments.map((a) => {
        if (!isAudioAttachment(a.content_type)) return null;
        /* width: 100% без min-width у audio в пустом пузыре даёт схлопывание до «полоски» */
        const shell = {
          width: "100%",
          minWidth: 260,
          maxWidth: 360,
          alignSelf: "stretch" as const,
        };
        if (!imageUrls[a.id]) {
          return <Skeleton key={`aud-sk-${a.id}`} height={38} radius="md" style={shell} />;
        }
        return (
          <Box key={`aud-wrap-${a.id}`} style={shell}>
            <ChatInlineAudioPlayer
              src={imageUrls[a.id]}
              allowDownload={allowAudioAttachmentDownload}
              style={{
                display: "block",
                width: "100%",
                height: 38,
              }}
            />
          </Box>
        );
      })}
      {attachments.some(
        (a) => !isAudioAttachment(a.content_type) && !isImageAttachment(a.content_type)
      ) ? (
        <Group gap="xs" wrap="wrap">
          {attachments.map((a) => {
            if (isAudioAttachment(a.content_type) || isImageAttachment(a.content_type)) return null;
            return (
              <Anchor
                key={`dl-${a.id}`}
                component="button"
                type="button"
                size="sm"
                onClick={async () => {
                  try {
                    const blob = await getBlob(a.id);
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = a.file_name;
                    link.click();
                    URL.revokeObjectURL(url);
                  } catch {
                    /* ignore */
                  }
                }}
                style={{ cursor: "pointer" }}
              >
                {a.file_name}
                {typeof a.size_bytes === "number" ? ` (${formatFileSize(a.size_bytes)})` : ""}
              </Anchor>
            );
          })}
        </Group>
      ) : null}
    </Stack>
  );
}
