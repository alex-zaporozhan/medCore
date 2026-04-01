import type { ActionIconProps } from "@mantine/core";
import { ActionIcon, Center, Loader, Popover } from "@mantine/core";
import { IconMoodSmile } from "@tabler/icons-react";
import { lazy, Suspense, useCallback, useState } from "react";
import { STAFF_FEED_CHROME } from "@/shared/staffFeedChrome";

const EmojiMartApplePickerPane = lazy(async () => {
  const mod = await import("./EmojiMartApplePickerPane");
  return { default: mod.EmojiMartApplePickerPane };
});

type EmojiSelectDetail = { native: string };

type Props = {
  onPick: (native: string) => void;
  /** После вставки эмодзи (например, вернуть фокус в поле ввода). */
  onInserted?: () => void;
  /** Подстройка под экран (по умолчанию — стиль стены персонала / brand). */
  actionIconProps?: Partial<ActionIconProps>;
  /** Класс для оболочки dropdown (стили em-emoji-picker в index.css). */
  dropdownClassName?: string;
  ariaLabel?: string;
};

/**
 * Общий emoji-mart (Apple, self-hosted sheet) в Popover для любых полей ввода.
 */
export function EmojiMartPopoverPicker({
  onPick,
  onInserted,
  actionIconProps,
  dropdownClassName = "emoji-mart-picker-shell",
  ariaLabel = "Эмодзи",
}: Props) {
  const [opened, setOpened] = useState(false);

  const handleSelect = useCallback(
    (detail: EmojiSelectDetail) => {
      const ch = detail?.native;
      if (ch) onPick(ch);
      setOpened(false);
      queueMicrotask(() => onInserted?.());
    },
    [onInserted, onPick]
  );

  return (
    <Popover
      opened={opened}
      onChange={setOpened}
      position="top"
      withArrow
      shadow="md"
      withinPortal
    >
      <Popover.Target>
        <ActionIcon
          {...STAFF_FEED_CHROME.actionIcon}
          {...actionIconProps}
          aria-label={ariaLabel}
          aria-expanded={opened}
          onClick={() => setOpened((o) => !o)}
        >
          <IconMoodSmile size={20} stroke={1.5} />
        </ActionIcon>
      </Popover.Target>
      <Popover.Dropdown
        p={0}
        className={dropdownClassName}
        style={{
          border: "none",
          background: "transparent",
          boxShadow: "none",
        }}
      >
        {opened ? (
          <Suspense
            fallback={
              <Center py="lg" px="xl" mih={200}>
                <Loader size="sm" type="dots" />
              </Center>
            }
          >
            <EmojiMartApplePickerPane onEmojiSelect={handleSelect} />
          </Suspense>
        ) : null}
      </Popover.Dropdown>
    </Popover>
  );
}
