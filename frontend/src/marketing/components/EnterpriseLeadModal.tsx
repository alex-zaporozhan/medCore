import { API_BASE, newOutboundRequestId } from "@/api/client";
import { TurnstileWidget } from "@/marketing/components/TurnstileWidget";
import { parseEnterpriseLeadSubmitFailure } from "@/marketing/enterpriseLeadPublic";
import { Button, Modal, Stack, Text, TextInput } from "@mantine/core";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

type EnterpriseLeadModalProps = {
  opened: boolean;
  onClose: () => void;
  /** Источник заявки в API (по умолчанию форма «Корпоратив»). */
  leadSource?: "corporate" | "sandbox_demo";
};

export function EnterpriseLeadModal({ opened, onClose, leadSource = "corporate" }: EnterpriseLeadModalProps) {
  const { t } = useTranslation("marketing");
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [contact, setContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [turnstileSiteKey, setTurnstileSiteKey] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

  const reset = useCallback(() => {
    setName("");
    setCompanyName("");
    setContact("");
    setError(null);
    setDone(false);
    setBusy(false);
    setTurnstileSiteKey(null);
    setTurnstileToken(null);
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [onClose, reset]);

  const doPost = useCallback(
    async (tokenOverride: string | null) => {
      setError(null);
      const n = name.trim();
      const c = companyName.trim();
      const p = contact.trim();
      if (!n || !c || !p) {
        setError(t("lead.fillAll"));
        return;
      }
      const captchaToken = tokenOverride?.trim();
      if (turnstileSiteKey && !captchaToken) {
        setError(t("lead.turnstile"));
        return;
      }
      setBusy(true);
      try {
        const body: Record<string, unknown> = {
          name: n,
          company_name: c,
          phone_or_email: p,
          lead_source: leadSource,
        };
        if (captchaToken) body.turnstile_token = captchaToken;
        const r = await fetch(`${API_BASE}/v1/platform-leads/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Request-Id": newOutboundRequestId(),
          },
          body: JSON.stringify(body),
        });
        const text = await r.text().catch(() => "");
        if (!r.ok) {
          const parsed = parseEnterpriseLeadSubmitFailure(r.status, text || "{}");
          const shown = parsed.code === "captcha_required" ? t("lead.turnstile") : parsed.message;
          if (parsed.code === "captcha_required" && parsed.siteKey) {
            setTurnstileSiteKey(parsed.siteKey);
            setTurnstileToken(null);
            setError(shown);
            return;
          }
          setTurnstileSiteKey(null);
          setTurnstileToken(null);
          setError(shown);
          return;
        }
        setTurnstileSiteKey(null);
        setTurnstileToken(null);
        setDone(true);
      } catch {
        setError(t("lead.sendFailed"));
      } finally {
        setBusy(false);
      }
    },
    [name, companyName, contact, leadSource, turnstileSiteKey, t],
  );

  const submit = useCallback(() => {
    const tok = turnstileSiteKey ? turnstileToken : null;
    void doPost(tok);
  }, [doPost, turnstileSiteKey, turnstileToken]);

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={t("lead.title")}
      radius="md"
      centered
    >
      {done ? (
        <Stack gap="md">
          <Text size="sm">{t("lead.success")}</Text>
          <Button onClick={handleClose} variant="light">
            {t("lead.close")}
          </Button>
        </Stack>
      ) : (
        <Stack gap="md">
          <TextInput label={t("lead.name")} value={name} onChange={(e) => setName(e.currentTarget.value)} required />
          <TextInput
            label={t("lead.company")}
            value={companyName}
            onChange={(e) => setCompanyName(e.currentTarget.value)}
            required
          />
          <TextInput
            label={t("lead.contact")}
            value={contact}
            onChange={(e) => setContact(e.currentTarget.value)}
            required
          />
          {turnstileSiteKey ? (
            <Stack gap="xs">
              <Text size="sm" fw={500}>
                {t("lead.captchaTitle")}
              </Text>
              <Text size="xs" c="dimmed">
                {t("lead.captchaHint")}
              </Text>
              <TurnstileWidget
                siteKey={turnstileSiteKey}
                onToken={(tok) => setTurnstileToken(tok)}
                onExpire={() => setTurnstileToken(null)}
              />
            </Stack>
          ) : null}
          {error ? (
            <Text size="sm" c="red">
              {error}
            </Text>
          ) : null}
          <Button onClick={() => void submit()} loading={busy}>
            {t("lead.submit")}
          </Button>
        </Stack>
      )}
    </Modal>
  );
}
