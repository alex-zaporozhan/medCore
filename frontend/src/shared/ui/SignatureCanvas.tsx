/**
 * Canvas-based signature pad for PWA. Produces base64 PNG for signature_payload.
 */

import { useRef, useState, useCallback, useEffect } from "react";
import { Box, Button, Stack, Text } from "@mantine/core";

export interface SignaturePayload {
  type: "drawn";
  image: string;
  meta?: {
    user_agent?: string;
    width?: number;
    height?: number;
  };
}

interface SignatureCanvasProps {
  width?: number;
  height?: number;
  onSignatureChange?: (payload: SignaturePayload | null) => void;
  disabled?: boolean;
  label?: string;
}

export function SignatureCanvas({
  width = 320,
  height = 160,
  onSignatureChange,
  disabled = false,
  label = "Подпись",
}: SignatureCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasStroke, setHasStroke] = useState(false);

  const getCanvas = useCallback(() => canvasRef.current ?? null, []);

  const clear = useCallback(() => {
    const canvas = getCanvas();
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasStroke(false);
    onSignatureChange?.(null);
  }, [getCanvas, onSignatureChange]);

  const emitPayload = useCallback(() => {
    const canvas = getCanvas();
    if (!canvas || !hasStroke) {
      onSignatureChange?.(null);
      return;
    }
    const dataUrl = canvas.toDataURL("image/png");
    const payload: SignaturePayload = {
      type: "drawn",
      image: dataUrl,
      meta: {
        user_agent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
        width: canvas.width,
        height: canvas.height,
      },
    };
    onSignatureChange?.(payload);
  }, [getCanvas, hasStroke, onSignatureChange]);

  useEffect(() => {
    if (hasStroke) emitPayload();
  }, [hasStroke, emitPayload]);

  useEffect(() => {
    const canvas = getCanvas();
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = typeof window !== "undefined" ? window.devicePixelRatio ?? 1 : 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);
    ctx.strokeStyle = "#1a1a1a";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
  }, [getCanvas, width, height]);

  const getCoords = (e: React.TouchEvent | React.MouseEvent) => {
    const canvas = getCanvas();
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    // Context is scaled by dpr, so 1 unit = 1 CSS pixel; use client coords relative to rect.
    if ("touches" in e) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top,
      };
    }
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };

  const startDraw = (e: React.TouchEvent | React.MouseEvent) => {
    e.preventDefault();
    if (disabled) return;
    const canvas = getCanvas();
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const { x, y } = getCoords(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e: React.TouchEvent | React.MouseEvent) => {
    e.preventDefault();
    if (!isDrawing || disabled) return;
    const canvas = getCanvas();
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const { x, y } = getCoords(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasStroke(true);
  };

  const endDraw = () => {
    setIsDrawing(false);
  };

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        {label}
      </Text>
      <Box
        style={{
          border: "1px solid var(--mantine-color-default-border)",
          borderRadius: "var(--mantine-radius-sm)",
          overflow: "hidden",
          background: "var(--mantine-color-gray-0)",
          touchAction: "none",
        }}
      >
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onMouseDown={startDraw}
          onMouseMove={draw}
          onMouseUp={endDraw}
          onMouseLeave={endDraw}
          onTouchStart={startDraw}
          onTouchMove={draw}
          onTouchEnd={endDraw}
          style={{ display: "block", cursor: disabled ? "not-allowed" : "crosshair" }}
        />
      </Box>
      <Button size="xs" variant="light" onClick={clear} disabled={disabled}>
        Очистить подпись
      </Button>
    </Stack>
  );
}
