import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  forwardRef,
  type UIEventHandler,
} from "react";
import { Box, Text, Textarea, type TextareaProps } from "@mantine/core";
import { useMergedRef } from "@mantine/hooks";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";

export type AppleEmojiOverlayTextareaProps = TextareaProps & {
  emojiEm?: number;
};

/**
 * Текстовое поле с зеркальным слоем: эмодзи как Apple-спрайт (как в пузырях), сам textarea с прозрачным текстом.
 * Нативный textarea иначе всегда рисует системный цветной шрифт (Segoe на Windows).
 */
export const AppleEmojiOverlayTextarea = forwardRef<HTMLTextAreaElement, AppleEmojiOverlayTextareaProps>(
  function AppleEmojiOverlayTextarea(
    { value, onScroll, placeholder, emojiEm = 1.12, styles: userStyles, ...rest },
    ref
  ) {
    const [scrollTop, setScrollTop] = useState(0);
    const [clipStyle, setClipStyle] = useState<React.CSSProperties>({});
    const [backdropLayout, setBackdropLayout] = useState<React.CSSProperties>({});
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const mergedRef = useMergedRef(ref, textareaRef);

    const str = typeof value === "string" ? value : "";

    const syncBackdrop = useCallback(() => {
      const el = textareaRef.current;
      if (!el) return;
      const s = getComputedStyle(el);
      setClipStyle({
        borderRadius: s.borderRadius,
      });
      setBackdropLayout({
        paddingTop: s.paddingTop,
        paddingRight: s.paddingRight,
        paddingBottom: s.paddingBottom,
        paddingLeft: s.paddingLeft,
        fontSize: s.fontSize,
        lineHeight: s.lineHeight,
        fontFamily: s.fontFamily,
        fontWeight: s.fontWeight,
        letterSpacing: s.letterSpacing,
        backgroundColor: s.backgroundColor,
      });
    }, []);

    useLayoutEffect(() => {
      syncBackdrop();
      const el = textareaRef.current;
      if (!el) return;
      const ro = new ResizeObserver(() => syncBackdrop());
      ro.observe(el);
      return () => ro.disconnect();
    }, [str, syncBackdrop]);

    const handleScroll: UIEventHandler<HTMLTextAreaElement> = (e) => {
      setScrollTop(e.currentTarget.scrollTop);
      onScroll?.(e);
    };

    const mergedStyles: TextareaProps["styles"] = (theme, props, ctx) => {
      const base =
        typeof userStyles === "function" ? userStyles(theme, props, ctx) : { ...(userStyles ?? {}) };
      return {
        ...base,
        input: {
          ...base?.input,
          position: "relative",
          zIndex: 1,
          backgroundColor: "transparent",
          color: "transparent",
          caretColor: "var(--mantine-color-text)",
          WebkitTextFillColor: "transparent",
        },
      };
    };

    return (
      <Box pos="relative">
        <Box
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            overflow: "hidden",
            pointerEvents: "none",
            zIndex: 0,
            ...clipStyle,
          }}
        >
          <Box
            style={{
              ...backdropLayout,
              transform: `translateY(-${scrollTop}px)`,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              boxSizing: "border-box",
              minHeight: "100%",
              color: "var(--mantine-color-text)",
            }}
          >
            {str ? (
              <AppleEmojiRichText text={str} emojiEm={emojiEm} />
            ) : placeholder ? (
              <Text span inherit c="dimmed" style={{ pointerEvents: "none" }}>
                {placeholder}
              </Text>
            ) : null}
          </Box>
        </Box>
        <Textarea
          ref={mergedRef}
          value={value}
          placeholder=""
          styles={mergedStyles}
          onScroll={handleScroll}
          {...rest}
        />
      </Box>
    );
  }
);
