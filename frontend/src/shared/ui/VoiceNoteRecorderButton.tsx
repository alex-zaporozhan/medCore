import { useCallback, useRef, useState } from "react";
import { ActionIcon, Tooltip } from "@mantine/core";
import { IconMicrophone, IconPlayerStop } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

type Props = {
  onRecorded: (file: File) => void;
  onError?: (message: string) => void;
  disabled?: boolean;
  maxDurationMs?: number;
};

function pickMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  if (MediaRecorder.isTypeSupported?.("audio/webm;codecs=opus")) {
    return "audio/webm;codecs=opus";
  }
  if (MediaRecorder.isTypeSupported?.("audio/webm")) {
    return "audio/webm";
  }
  return undefined;
}

/**
 * Короткий fade-in на входе записи через Web Audio, чтобы убрать стартовый щелчок/«импульс»
 * у MediaRecorder (особенно webm/opus) при резком включении микрофона.
 */
async function buildRecordStreamWithFadeIn(rawStream: MediaStream): Promise<{
  recordStream: MediaStream;
  releaseGraph: () => void;
}> {
  const Ctx =
    typeof AudioContext !== "undefined"
      ? AudioContext
      : (typeof window !== "undefined"
          ? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
          : undefined);
  if (!Ctx) {
    throw new Error("AudioContext unavailable");
  }
  const ctx = new Ctx();
  await ctx.resume();
  const source = ctx.createMediaStreamSource(rawStream);
  const gain = ctx.createGain();
  const t0 = ctx.currentTime;
  gain.gain.setValueAtTime(0, t0);
  gain.gain.linearRampToValueAtTime(1, t0 + 0.04);
  const dest = ctx.createMediaStreamDestination();
  source.connect(gain);
  gain.connect(dest);
  const releaseGraph = () => {
    try {
      source.disconnect();
      gain.disconnect();
      dest.disconnect();
      void ctx.close();
    } catch {
      /* ignore */
    }
  };
  return { recordStream: dest.stream, releaseGraph };
}

/**
 * Запись голоса в браузере (MediaRecorder → webm), старт/стоп по клику.
 */
export function VoiceNoteRecorderButton({
  onRecorded,
  onError,
  disabled,
  maxDurationMs = 120_000,
}: Props) {
  const { t } = useTranslation("chat");
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const recRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const releaseGraphRef = useRef<(() => void) | null>(null);

  const stopInternal = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const rec = recRef.current;
    recRef.current = null;
    if (rec && rec.state !== "inactive") {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    releaseGraphRef.current?.();
    releaseGraphRef.current = null;
    const st = streamRef.current;
    streamRef.current = null;
    if (st) {
      st.getTracks().forEach((t) => t.stop());
    }
    setRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    if (disabled || recording) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      const msg = t("errors.micUnavailable");
      setError(msg);
      onError?.(msg);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      streamRef.current = stream;
      chunksRef.current = [];

      let recordStream: MediaStream = stream;
      try {
        const { recordStream: faded, releaseGraph } = await buildRecordStreamWithFadeIn(stream);
        recordStream = faded;
        releaseGraphRef.current = releaseGraph;
      } catch {
        releaseGraphRef.current = null;
      }

      const mime = pickMime();
      const rec = mime ? new MediaRecorder(recordStream, { mimeType: mime }) : new MediaRecorder(recordStream);
      recRef.current = rec;
      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      rec.onerror = () => {
        const msg = t("errors.recordFailed");
        setError(msg);
        onError?.(msg);
        stopInternal();
      };
      rec.onstop = () => {
        const parts = chunksRef.current;
        chunksRef.current = [];
        const blob = new Blob(parts, { type: rec.mimeType || "audio/webm" });
        if (blob.size > 0) {
          const name = `voice-${Date.now()}.webm`;
          onRecorded(new File([blob], name, { type: blob.type }));
        }
        stopInternal();
      };
      rec.start(200);
      setRecording(true);
      timerRef.current = window.setTimeout(() => {
        if (recRef.current && recRef.current.state === "recording") {
          try {
            recRef.current.stop();
          } catch {
            /* ignore */
          }
        }
      }, maxDurationMs);
    } catch {
      const msg = t("errors.micDenied");
      setError(msg);
      onError?.(msg);
      stopInternal();
    }
  }, [disabled, maxDurationMs, onError, onRecorded, recording, stopInternal, t]);

  const toggle = useCallback(() => {
    if (recording) {
      const rec = recRef.current;
      if (rec && rec.state === "recording") {
        rec.stop();
      }
    } else {
      void startRecording();
    }
  }, [recording, startRecording]);

  return (
    <Tooltip label={error || (recording ? t("voice.stop") : t("voice.tooltip"))}>
      <ActionIcon
        variant={recording ? "filled" : "light"}
        color={recording ? "red" : "gray"}
        size="lg"
        aria-label={recording ? t("voice.stop") : t("voice.record")}
        disabled={disabled}
        onClick={toggle}
      >
        {recording ? <IconPlayerStop size={20} /> : <IconMicrophone size={20} />}
      </ActionIcon>
    </Tooltip>
  );
}
