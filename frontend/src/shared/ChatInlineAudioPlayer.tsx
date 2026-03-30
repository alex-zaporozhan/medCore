import type { CSSProperties } from "react";
import { useEffect, useRef } from "react";
import { notifyChatAudioPlay, notifyChatAudioStopped } from "@/shared/chatAudioCoordinator";

type Props = {
  src: string;
  /** false — скрыть пункт «скачать» в нативных controls (Chrome). */
  allowDownload?: boolean;
  className?: string;
  style?: CSSProperties;
};

function pickAudioContextCtor(): (typeof AudioContext) | null {
  if (typeof AudioContext !== "undefined") return AudioContext;
  const w = typeof window !== "undefined" ? (window as unknown as { webkitAudioContext?: typeof AudioContext }) : undefined;
  return w?.webkitAudioContext ?? null;
}

/**
 * Голосовые вложения в чатах: один активный плеер + смягчение старта.
 *
 * Почему бывает «щелчок» у <audio>:
 * - у кодеков (часто webm/opus у записи с микрофона) в начале потока есть преамбула/выравнивание декодера;
 * - резкий переход «тишина → сигнал» даёт широкополосный щелчок в ЦАП;
 * - element.volume меняется не синхронно с аудиотактом, часть первых сэмплов может пройти без затухания.
 *
 * Сильнее, чем rAF+volume: MediaElementSource → GainNode и экспоненциальный ramp по audio-времени контекста.
 */
export function ChatInlineAudioPlayer({
  src,
  allowDownload = false,
  className,
  style,
}: Props) {
  const ref = useRef<HTMLAudioElement>(null);
  const rampFrame = useRef<number | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const cancelVolumeRamp = () => {
      if (rampFrame.current != null) {
        cancelAnimationFrame(rampFrame.current);
        rampFrame.current = null;
      }
    };

    const Ctor = pickAudioContextCtor();
    let graph: { ctx: AudioContext; gain: GainNode; useWebAudio: boolean } | null = null;

    if (Ctor) {
      try {
        const ctx = new Ctor();
        const source = ctx.createMediaElementSource(el);
        const gain = ctx.createGain();
        gain.gain.value = 1;
        source.connect(gain);
        gain.connect(ctx.destination);
        el.volume = 1;
        graph = { ctx, gain, useWebAudio: true };
      } catch {
        graph = null;
      }
    }

    const onPlay = () => {
      notifyChatAudioPlay(el);

      if (graph?.useWebAudio) {
        void graph.ctx.resume().then(() => {
          const g = graph!.gain.gain;
          const t0 = graph!.ctx.currentTime;
          g.cancelScheduledValues(t0);
          g.setValueAtTime(0.0001, t0);
          /* ~110 ms: экспонента мягче у края, чем линейный volume по rAF */
          try {
            g.exponentialRampToValueAtTime(1, t0 + 0.11);
          } catch {
            g.linearRampToValueAtTime(1, t0 + 0.11);
          }
        });
        return;
      }

      cancelVolumeRamp();
      el.volume = 0.0001;
      const t0 = performance.now();
      const ms = 120;
      const tick = () => {
        if (el.paused) {
          cancelVolumeRamp();
          el.volume = 1;
          return;
        }
        const u = Math.min(1, (performance.now() - t0) / ms);
        el.volume = Math.max(0.0001, u);
        if (u < 1) {
          rampFrame.current = requestAnimationFrame(tick);
        } else {
          el.volume = 1;
          rampFrame.current = null;
        }
      };
      rampFrame.current = requestAnimationFrame(tick);
    };

    const onPause = () => {
      notifyChatAudioStopped(el);
      cancelVolumeRamp();
      el.volume = 1;
      if (graph?.useWebAudio) {
        const g = graph.gain.gain;
        const t = graph.ctx.currentTime;
        g.cancelScheduledValues(t);
        g.setValueAtTime(1, t);
      }
    };

    el.addEventListener("play", onPlay);
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onPause);
    return () => {
      el.removeEventListener("play", onPlay);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onPause);
      cancelVolumeRamp();
      notifyChatAudioStopped(el);
      if (graph?.useWebAudio) {
        try {
          graph.ctx.close();
        } catch {
          /* ignore */
        }
      }
    };
  }, [src]);

  return (
    <audio
      key={src}
      ref={ref}
      controls
      className={className}
      controlsList={allowDownload ? undefined : "nodownload"}
      src={src}
      style={style}
      preload="metadata"
    />
  );
}
