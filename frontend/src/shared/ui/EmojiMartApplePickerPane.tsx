/** Для `set="apple"` нужны `x`/`y` под spritesheet; дефолтный `@emoji-mart/data` — native без координат → сетка `#`. */
import data from "@emoji-mart/data/sets/15/apple.json";
import i18nRu from "@emoji-mart/data/i18n/ru.json";
import Picker from "@emoji-mart/react";
import { emojiMartAppleSpritesheetUrl } from "@/shared/emojiMartAppleAssets";

type EmojiSelectDetail = { native: string };

type Props = {
  onEmojiSelect: (detail: EmojiSelectDetail) => void;
};

/**
 * Тяжёлый слой пикера: отдельный чанк. Apple-глифы через self-hosted spritesheet
 * (см. scripts/sync-emoji-apple-sheet.mjs), без cdn.jsdelivr.net.
 */
export function EmojiMartApplePickerPane({ onEmojiSelect }: Props) {
  const sheetUrl = emojiMartAppleSpritesheetUrl();
  return (
    <Picker
      data={data}
      i18n={i18nRu}
      theme="light"
      set="apple"
      locale="ru"
      previewPosition="none"
      skinTonePosition="search"
      dynamicWidth
      perLine={8}
      maxFrequentRows={1}
      emojiButtonRadius="8px"
      emojiSize={22}
      getSpritesheetURL={() => sheetUrl}
      onEmojiSelect={onEmojiSelect}
    />
  );
}
