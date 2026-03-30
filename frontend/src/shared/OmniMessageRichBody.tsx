import { Fragment, useMemo } from "react";
import { Anchor } from "@mantine/core";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { ClinicChatAttachments } from "@/shared/ClinicChatAttachments";
import {
  shouldOmitChatBodyForAudioAttachment,
  shouldOmitOmniMediaPlaceholder,
} from "@/shared/chatMessageBodyDisplay";

export type OmniMessageAttachmentView = {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  source: "omni" | "clinic_chat";
  conversation_id?: string | null;
};

const URL_IN_TEXT = /(https?:\/\/[^\s<>"']+)/gi;

function isProbablyImageUrl(u: string): boolean {
  return /\.(png|jpe?g|gif|webp|avif)(\?|#|$)/i.test(u);
}

function splitTextAndUrls(text: string): Array<{ kind: "text"; s: string } | { kind: "url"; s: string }> {
  if (!text) return [];
  const parts: Array<{ kind: "text" | "url"; s: string }> = [];
  let last = 0;
  let m: RegExpExecArray | null;
  const re = new RegExp(URL_IN_TEXT.source, URL_IN_TEXT.flags);
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      parts.push({ kind: "text", s: text.slice(last, m.index) });
    }
    parts.push({ kind: "url", s: m[1] });
    last = m.index + m[1].length;
  }
  if (last < text.length) {
    parts.push({ kind: "text", s: text.slice(last) });
  }
  return parts.length ? parts : [{ kind: "text", s: text }];
}

type Props = {
  content: string;
  attachments: OmniMessageAttachmentView[];
  /** Авторизованная загрузка вложений из PWA-чата (мост). */
  getClinicChatBlob: (conversationId: string, attachmentId: string) => Promise<Blob>;
  /** Авторизованная загрузка файлов, сохранённых в omnichannel. */
  getOmniBlob: (attachmentId: string) => Promise<Blob>;
  /** Только роль владельца: скачивание audio/* из чата. */
  allowAudioAttachmentDownload?: boolean;
};

/**
 * Тело сообщения омниканала: эмодзи Apple, ссылки (картинки по URL — превью), вложения.
 */
export function OmniMessageRichBody({
  content,
  attachments,
  getClinicChatBlob,
  getOmniBlob,
  allowAudioAttachmentDownload = false,
}: Props) {
  const segments = useMemo(() => splitTextAndUrls(content || ""), [content]);
  const briefTypes = attachments.map((a) => ({ content_type: a.content_type }));
  const omitText =
    shouldOmitChatBodyForAudioAttachment(content, briefTypes) ||
    shouldOmitOmniMediaPlaceholder(content, briefTypes);

  const getBlob = useMemo(() => {
    return async (attachmentId: string) => {
      const att = attachments.find((a) => a.id === attachmentId);
      if (!att) throw new Error("attachment not found");
      if (att.source === "clinic_chat" && att.conversation_id) {
        return getClinicChatBlob(att.conversation_id, attachmentId);
      }
      return getOmniBlob(attachmentId);
    };
  }, [attachments, getClinicChatBlob, getOmniBlob]);

  const briefs = attachments.map((a) => ({
    id: a.id,
    file_name: a.file_name,
    content_type: a.content_type,
    size_bytes: a.size_bytes,
  }));

  return (
    <>
      {!omitText
        ? segments.map((seg, i) => (
            <Fragment key={i}>
              {seg.kind === "text" ? (
                <AppleEmojiRichText text={seg.s} />
              ) : isProbablyImageUrl(seg.s) ? (
                <a href={seg.s} target="_blank" rel="noopener noreferrer">
                  <img
                    src={seg.s}
                    alt=""
                    style={{ maxWidth: "100%", maxHeight: 220, borderRadius: 8, display: "block", marginTop: 6 }}
                  />
                </a>
              ) : (
                <Anchor href={seg.s} target="_blank" rel="noopener noreferrer" size="sm" style={{ wordBreak: "break-all" }}>
                  {seg.s}
                </Anchor>
              )}
            </Fragment>
          ))
        : null}
      {briefs.length > 0 ? (
        <ClinicChatAttachments
          attachments={briefs}
          getBlob={getBlob}
          allowAudioAttachmentDownload={allowAudioAttachmentDownload}
        />
      ) : null}
    </>
  );
}
