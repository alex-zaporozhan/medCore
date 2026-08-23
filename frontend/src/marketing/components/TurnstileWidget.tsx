import { Box, Text } from "@mantine/core";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

const TURNSTILE_SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement | string,
        options: {
          sitekey: string;
          callback?: (token: string) => void;
          "error-callback"?: () => void;
          "expired-callback"?: () => void;
        },
      ) => string;
      remove?: (widgetId: string) => void;
      reset?: (widgetId: string) => void;
    };
  }
}

type TurnstileWidgetProps = {
  siteKey: string;
  onToken: (token: string) => void;
  onExpire?: () => void;
};

let turnstileScriptPromise: Promise<void> | null = null;

function ensureTurnstileScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.turnstile) return Promise.resolve();
  if (turnstileScriptPromise) return turnstileScriptPromise;
  turnstileScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${TURNSTILE_SCRIPT}"]`);
    if (existing) {
      if (window.turnstile) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("turnstile script")), { once: true });
      return;
    }
    const s = document.createElement("script");
    s.src = TURNSTILE_SCRIPT;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("turnstile script"));
    document.head.appendChild(s);
  });
  return turnstileScriptPromise;
}

/**
 * Виджет Cloudflare Turnstile для публичного checkout (адаптивный порог на backend).
 */
export function TurnstileWidget({ siteKey, onToken, onExpire }: TurnstileWidgetProps) {
  const { t } = useTranslation("marketing");
  const hostRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadErr(null);
    void ensureTurnstileScript()
      .then(() => {
        if (cancelled || !hostRef.current || !window.turnstile) return;
        if (widgetIdRef.current && window.turnstile.remove) {
          window.turnstile.remove(widgetIdRef.current);
          widgetIdRef.current = null;
        }
        const id = window.turnstile.render(hostRef.current, {
          sitekey: siteKey,
          callback: (t) => onToken(t),
          "expired-callback": () => onExpire?.(),
        });
        widgetIdRef.current = id;
      })
      .catch(() => {
        if (!cancelled) setLoadErr(t("checkout.turnstileLoad"));
      });
    return () => {
      cancelled = true;
      if (widgetIdRef.current && window.turnstile?.remove) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [siteKey, onToken, onExpire, t]);

  return (
    <Box>
      {loadErr ? (
        <Text size="sm" c="red">
          {loadErr}
        </Text>
      ) : null}
      <div ref={hostRef} data-testid="turnstile-host" />
    </Box>
  );
}
