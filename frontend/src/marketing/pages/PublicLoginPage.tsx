import { SignInShell } from "@/auth/SignInShell";
import { ClinicStaffSignInPanel } from "@/auth/panels/ClinicStaffSignInPanel";
import {
  Alert,
  Button,
  Divider,
  Group,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function PublicLoginPage() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [patientSlug, setPatientSlug] = useState("");

  const patientEntryHint = useMemo(() => {
    const v = searchParams.get("patientEntry");
    if (v === "need-clinic") {
      return t("public.hintNeedClinic");
    }
    if (v === "patient-url-needs-clinic-slug") {
      return t("public.hintNeedsSlug");
    }
    if (v === "session-expired") {
      return t("public.hintSessionExpired");
    }
    if (v === "oauth-cancelled" || v === "oauth-error") {
      return t("public.hintOauth");
    }
    return null;
  }, [searchParams, t]);

  const goPatientBySlug = () => {
    const raw = patientSlug.trim().replace(/^\/+|\/+$/g, "");
    if (!raw) return;
    const slug = raw.replace(/^c\//i, "").split("/")[0]?.trim();
    if (!slug) return;
    navigate(`/c/${encodeURIComponent(slug)}/sign-in`);
  };

  return (
    <SignInShell>
      <Stack gap="xl">
        <div>
          <Title order={2}>{t("public.pageTitle")}</Title>
          <Text size="sm" c="dimmed" mt={6}>
            {t("public.pageSubtitle")}
          </Text>
        </div>

        {patientEntryHint ? (
          <Alert color="slate" variant="light" title={t("public.patientAlertTitle")}>
            {patientEntryHint}
          </Alert>
        ) : null}

        <Stack gap="sm">
          <Text size="sm" fw={600}>
            {t("public.patientsHeading")}
          </Text>
          <Text size="xs" c="dimmed">
            {t("public.patientsHelp")}
          </Text>
          <Text size="xs" c="dimmed">
            {t("public.ownerSlugHelp")}
          </Text>
          <Group gap="xs" align="flex-end" wrap="nowrap">
            <TextInput
              flex={1}
              label={t("public.clinicSlugLabel")}
              placeholder={t("public.clinicSlugPlaceholder")}
              value={patientSlug}
              onChange={(e) => setPatientSlug(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") goPatientBySlug();
              }}
            />
            <Button variant="filled" color="slate" onClick={goPatientBySlug}>
              {t("public.patientContinue")}
            </Button>
          </Group>
        </Stack>

        <Divider label={t("public.staffDivider")} labelPosition="center" />

        <ClinicStaffSignInPanel />
      </Stack>
    </SignInShell>
  );
}
