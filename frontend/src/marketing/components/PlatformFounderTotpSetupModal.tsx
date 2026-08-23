import { API_BASE, parseFastApiErrorBody } from "@/api/client";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import {
  Alert,
  Button,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";

type Props = {
  opened: boolean;
  onClose: () => void;
};

/**
 * Привязка Google Authenticator / TOTP к учётной записи Основателя (POST enroll + confirm).
 */
export function PlatformFounderTotpSetupModal({ opened, onClose }: Props) {
  const { t } = useTranslation("founder");
  const { token, setToken } = usePlatformFounderSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [otpauthUri, setOtpauthUri] = useState<string | null>(null);
  const [issuer, setIssuer] = useState<string | null>(null);
  const [accountEmail, setAccountEmail] = useState<string | null>(null);
  const [confirmCode, setConfirmCode] = useState("");

  const reset = () => {
    setError(null);
    setOtpauthUri(null);
    setIssuer(null);
    setAccountEmail(null);
    setConfirmCode("");
  };

  const handleClose = () => {
    if (!busy) {
      reset();
      onClose();
    }
  };

  const enroll = async () => {
    setError(null);
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/platform/auth/totp/enroll`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      const text = await r.text().catch(() => "");
      if (r.status === 409) {
        setError(t("totp.alreadyOn"));
        return;
      }
      if (!r.ok) {
        const p = parseFastApiErrorBody(text || "{}");
        setError(p.rawMessage?.trim() || t("errors.status", { status: r.status }));
        return;
      }
      const data = JSON.parse(text) as { otpauth_uri?: string; issuer?: string; account_email?: string };
      if (data.otpauth_uri) setOtpauthUri(data.otpauth_uri);
      if (data.issuer) setIssuer(data.issuer);
      if (data.account_email) setAccountEmail(data.account_email);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("errors.network"));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setError(null);
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/platform/auth/totp/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ code: confirmCode.trim() }),
      });
      const text = await r.text().catch(() => "");
      if (!r.ok) {
        const p = parseFastApiErrorBody(text || "{}");
        setError(p.rawMessage?.trim() || t("errors.status", { status: r.status }));
        return;
      }
      const data = JSON.parse(text) as { access_token?: string };
      if (typeof data.access_token === "string" && data.access_token) {
        setToken(data.access_token);
      }
      reset();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("errors.network"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={handleClose} title={t("totp.title")} size="md" centered>
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          {t("totp.lead")}
        </Text>

        {!otpauthUri ? (
          <Button loading={busy} onClick={() => void enroll()}>
            {t("totp.generate")}
          </Button>
        ) : (
          <>
            {issuer || accountEmail ? (
              <Text size="sm">
                {issuer ? (
                  <>
                    {t("totp.issuer")} <Text span ff="monospace">{issuer}</Text>
                    <br />
                  </>
                ) : null}
                {accountEmail ? (
                  <>
                    {t("totp.account")} <Text span ff="monospace">{accountEmail}</Text>
                  </>
                ) : null}
              </Text>
            ) : null}
            <Text size="xs" ff="monospace" style={{ wordBreak: "break-all" }}>
              {otpauthUri}
            </Text>
            <TextInput
              label={t("totp.confirmCode")}
              placeholder="000000"
              value={confirmCode}
              onChange={(e) => setConfirmCode(e.currentTarget.value)}
              autoComplete="one-time-code"
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={reset} disabled={busy}>
                {t("totp.reset")}
              </Button>
              <Button loading={busy} onClick={() => void confirm()} disabled={confirmCode.trim().length < 6}>
                {t("totp.confirmEnable")}
              </Button>
            </Group>
          </>
        )}

        {error ? (
          <Alert color="red" variant="light" title={t("totp.errorTitle")}>
            {error}
          </Alert>
        ) : null}
      </Stack>
    </Modal>
  );
}
