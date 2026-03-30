/**
 * Не показывать текст тела, если он только служебные плейсхолдеры, а аудио уже рендерится плеером.
 */
export function shouldOmitChatBodyForAudioAttachment(
  body: string | null | undefined,
  attachments: Array<{ content_type: string }> | null | undefined,
  messageType?: string | null,
): boolean {
  if (messageType === "sticker") return false;
  const atts = attachments ?? [];
  if (!atts.some((a) => (a.content_type || "").toLowerCase().startsWith("audio/"))) {
    return false;
  }
  const t = (body || "").trim();
  if (!t) return true;
  if (t === "[Голосовое сообщение]") return true;
  if (/^\[Вложение:[^\]]+\]$/.test(t)) return true;
  const stripped = t
    .replace(/\s*\[Вложение:[^\]]+\]\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return stripped === "" || stripped === "[Голосовое сообщение]";
}

const OMNI_MEDIA_PLACEHOLDERS = new Set([
  "",
  "[Изображение]",
  "[Вложение]",
  "[Голосовое сообщение]",
]);

/** Скрыть текст омни-сообщения, если это только служебный плейсхолдер при наличии вложений. */
export function shouldOmitOmniMediaPlaceholder(
  content: string | null | undefined,
  attachments: Array<{ content_type: string }> | null | undefined,
): boolean {
  const atts = attachments ?? [];
  if (atts.length === 0) return false;
  const t = (content || "").trim();
  return OMNI_MEDIA_PLACEHOLDERS.has(t);
}
