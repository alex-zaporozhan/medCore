import appleData from "@emoji-mart/data/sets/15/apple.json";
import type { EmojiMartData } from "@emoji-mart/data";

const data = appleData as EmojiMartData;

/** native (включая тон кожи / ZWJ) → координаты в sheets-256/64.png */
export function buildNativeAppleSpriteMap(): Map<string, { x: number; y: number }> {
  const m = new Map<string, { x: number; y: number }>();
  for (const emoji of Object.values(data.emojis)) {
    for (const skin of emoji.skins) {
      if (skin.x === undefined || skin.y === undefined) continue;
      const pos = { x: skin.x, y: skin.y };
      const n = skin.native;
      m.set(n, pos);
      try {
        const nfc = n.normalize("NFC");
        if (nfc !== n) m.set(nfc, pos);
      } catch {
        /* ignore */
      }
    }
  }
  return m;
}

export const NATIVE_APPLE_SPRITE_MAP: Map<string, { x: number; y: number }> =
  buildNativeAppleSpriteMap();

export const APPLE_SHEET_DIMS = data.sheet;
