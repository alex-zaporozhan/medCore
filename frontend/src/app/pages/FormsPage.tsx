import { useState } from "react";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { usePatientPendingForms, useSubmitPatientForm } from "@/hooks";
import {
  Button,
  Card,
  Checkbox,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import type { DigitalFormFieldSchema, DigitalFormTemplate } from "@/api/types";
import { SignatureCanvas, type SignaturePayload } from "@/shared/ui/SignatureCanvas";
import { QueryErrorAlert } from "@/shared/ui";
import { SEMANTIC } from "@/shared/semanticUi";
import { useTranslation } from "react-i18next";

type FormValues = Record<string, unknown>;

function renderField(
  field: DigitalFormFieldSchema,
  value: unknown,
  onChange: (v: unknown) => void,
  datePlaceholder: string,
) {
  switch (field.type) {
    case "text":
      return (
        <TextInput
          label={field.label}
          required={field.required}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
    case "textarea":
      return (
        <Textarea
          label={field.label}
          required={field.required}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
          minRows={3}
        />
      );
    case "number":
      return (
        <NumberInput
          label={field.label}
          required={field.required}
          value={typeof value === "number" ? value : undefined}
          onChange={(val) => onChange(typeof val === "number" ? val : undefined)}
        />
      );
    case "select":
      return (
        <Select
          label={field.label}
          required={field.required}
          data={(field.options ?? []).map((o) => ({ value: o, label: o }))}
          value={typeof value === "string" ? value : null}
          onChange={(v) => onChange(v ?? undefined)}
        />
      );
    case "checkbox":
      if (field.options && field.options.length > 0) {
        const arr = Array.isArray(value) ? (value as string[]) : [];
        return (
          <Stack gap={4}>
            <Text size="sm" fw={500}>
              {field.label}
            </Text>
            {field.options.map((opt) => {
              const checked = arr.includes(opt);
              return (
                <Checkbox
                  key={opt}
                  label={opt}
                  checked={checked}
                  onChange={(e) => {
                    if (e.currentTarget.checked) {
                      onChange([...arr, opt]);
                    } else {
                      onChange(arr.filter((x) => x !== opt));
                    }
                  }}
                />
              );
            })}
          </Stack>
        );
      }
      return (
        <Checkbox
          label={field.label}
          checked={typeof value === "boolean" ? value : false}
          onChange={(e) => onChange(e.currentTarget.checked)}
        />
      );
    case "date":
      return (
        <TextInput
          label={field.label}
          required={field.required}
          placeholder={datePlaceholder}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
    default:
      return (
        <TextInput
          label={field.label}
          required={field.required}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
  }
}

export default function FormsPage() {
  const { t } = useTranslation("patient");
  const { accessToken } = usePatientAuth();
  const { data: templates, isLoading, isError, error } = usePatientPendingForms(accessToken);
  const submitForm = useSubmitPatientForm(accessToken);
  const [selectedTemplate, setSelectedTemplate] = useState<DigitalFormTemplate | null>(null);
  const [values, setValues] = useState<FormValues>({});
  const [signaturePayload, setSignaturePayload] = useState<SignaturePayload | null>(null);
  const [signerName, setSignerName] = useState("");

  const handleStart = (tmpl: DigitalFormTemplate) => {
    setSelectedTemplate(tmpl);
    const initial: FormValues = {};
    tmpl.schema.fields.forEach((f) => {
      initial[f.id] = undefined;
    });
    setValues(initial);
    setSignaturePayload(null);
    setSignerName("");
  };

  const handleChange = (fieldId: string, v: unknown) => {
    setValues((prev) => ({ ...prev, [fieldId]: v }));
  };

  const handleSubmit = () => {
    if (!selectedTemplate) return;
    if (selectedTemplate.requires_signature && !signaturePayload) {
      return;
    }
    submitForm.mutate(
      {
        templateCode: selectedTemplate.code,
        body: {
          data: values,
          signature_payload: signaturePayload ?? undefined,
          signer_name: signerName || undefined,
        },
      },
      {
        onSuccess: () => {
          setSelectedTemplate(null);
          setSignaturePayload(null);
        },
      }
    );
  };

  const canSubmit =
    selectedTemplate &&
    (!selectedTemplate.requires_signature || signaturePayload !== null);

  if (isLoading) {
    return <Text>{t("forms.loading")}</Text>;
  }
  if (isError) {
    return (
      <Stack>
        <Title order={3}>{t("forms.title")}</Title>
        <QueryErrorAlert error={error} title={t("forms.loadFailed")} />
      </Stack>
    );
  }

  if (!selectedTemplate) {
    return (
      <Stack>
        <Title order={3}>{t("forms.title")}</Title>
        {!templates?.length && (
          <Text size="sm" c="dimmed">
            {t("forms.empty")}
          </Text>
        )}
        {templates?.map((tmpl) => (
          <Card
            key={tmpl.id}
            withBorder
            radius="md"
            shadow="xs"
            className="interactive-card"
            onClick={() => handleStart(tmpl)}
          >
            <Stack gap={4}>
              <Text fw={600}>{tmpl.name}</Text>
              <Text size="sm" c="dimmed">
                {t("forms.code", { code: tmpl.code })}
              </Text>
              {tmpl.requires_signature && (
                <Text size="xs" c="dimmed">
                  {t("forms.needsSignature")}
                </Text>
              )}
            </Stack>
          </Card>
        ))}
      </Stack>
    );
  }

  return (
    <Stack>
      <Title order={3}>{selectedTemplate.name}</Title>
      <Text size="sm" c="dimmed">
        {t("forms.fillHint")}
      </Text>
      <Stack gap="sm">
        {selectedTemplate.schema.fields.map((field) => (
          <div key={field.id}>
            {renderField(field, values[field.id], (v) => handleChange(field.id, v), t("forms.datePlaceholder"))}
          </div>
        ))}
        {selectedTemplate.requires_signature && (
          <>
            <TextInput
              label={t("forms.signerName")}
              placeholder={t("forms.signerPlaceholder")}
              value={signerName}
              onChange={(e) => setSignerName(e.currentTarget.value)}
            />
            <SignatureCanvas
              label={t("forms.signature")}
              onSignatureChange={setSignaturePayload}
              disabled={submitForm.isPending}
            />
            {!signaturePayload && (
              <Text size="xs" c="dimmed">
                {t("forms.signHint")}
              </Text>
            )}
          </>
        )}
      </Stack>
      <Group justify="flex-end" mt="md">
        <Button variant="subtle" color={SEMANTIC.action.dismiss} onClick={() => setSelectedTemplate(null)}>
          {t("forms.cancel")}
        </Button>
        <Button
          color={SEMANTIC.action.confirm}
          onClick={handleSubmit}
          loading={submitForm.isPending}
          disabled={!canSubmit}
        >
          {t("forms.submit")}
        </Button>
      </Group>
    </Stack>
  );
}

