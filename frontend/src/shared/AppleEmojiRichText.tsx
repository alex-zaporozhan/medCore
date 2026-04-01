import { Fragment, useMemo } from "react";
import { emojiMartAppleSpritesheetUrl } from "@/shared/emojiMartAppleAssets";
import { APPLE_SHEET_DIMS, NATIVE_APPLE_SPRITE_MAP } from "@/shared/appleEmojiSpriteMap";

function graphemeSegments(text: string): string[] {
  if (typeof Intl !== "undefined" && "Segmenter" in Intl) {
    const seg = new Intl.Segmenter("en", { granularity: "grapheme" });
    return Array.from(seg.segment(text), (s: Intl.SegmentData) => s.segment);
  }
  return Array.from(text);
}

type Props = {
  text: string;
  /** Относительный размер глифа к размеру шрифта строки */
  emojiEm?: number;
};

/**
 * Обычный текст + эмодзи как Apple-спрайт (тот же PNG, что у emoji-mart picker),
 * чтобы на Windows не показывались «плоские» системные смайлики.
 */
export function AppleEmojiRichText({ text, emojiEm = 1.12 }: Props) {
  const sheetUrl = emojiMartAppleSpritesheetUrl();
  const { cols, rows } = APPLE_SHEET_DIMS;

  const nodes = useMemo(() => {
    const parts = graphemeSegments(text);
    return parts.map((segment, i) => {
      if (segment === "") return null;
      let pos = NATIVE_APPLE_SPRITE_MAP.get(segment);
      if (!pos) {
        try {
          pos = NATIVE_APPLE_SPRITE_MAP.get(segment.normalize("NFC"));
        } catch {
          pos = undefined;
        }
      }
      if (!pos) {
        return <Fragment key={i}>{segment}</Fragment>;
      }
      const x = pos.x;
      const y = pos.y;
      return (
        <span
          key={i}
          className="apple-emoji-sprite"
          style={{
            display: "inline-block",
            width: `${emojiEm}em`,
            height: `${emojiEm}em`,
            verticalAlign: "-0.2em",
            backgroundImage: `url(${sheetUrl})`,
            backgroundRepeat: "no-repeat",
            backgroundSize: `${100 * cols}% ${100 * rows}%`,
            backgroundPosition: `${(100 / (cols - 1)) * x}% ${(100 / (rows - 1)) * y}%`,
          }}
          role="img"
          aria-label={segment}
        />
      );
    });
  }, [cols, emojiEm, rows, sheetUrl, text]);

  return <>{nodes}</>;
}
