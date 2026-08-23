import { API_BASE, newOutboundRequestId } from "@/api/client";
import { tNs } from "@/i18n";
import { EnterpriseLeadModal } from "@/marketing/components/EnterpriseLeadModal";
import {
  formatCatalogUsdLabel,
  isMarketingPlanSlug,
  marketingOverlayForSlug,
  marketingPlanCopy,
  parseCatalogAmount,
  sortPublicPlanRowsByMarketingOrder,
} from "@/marketing/marketingPublicPlans";
import { catalogFetchErrorMessage, parsePublicCheckoutFailure } from "@/marketing/platformBillingPublic";
import { labelForEntitlementKey } from "@/shared/entitlementDisplay";
import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  List,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { TurnstileWidget } from "./TurnstileWidget";

export type PublicPlanRow = {
  slug: string;
  display_name: string;
  description?: string | null;
  option_keys?: string[];
  price_monthly_rub?: string | null;
  price_annual_rub?: string | null;
  currency?: string | null;
};

export type PublicCatalogOption = {
  entitlement_key: string;
  display_name: string;
  description?: string | null;
  list_price_rub?: string | null;
  currency?: string | null;
};

type PlatformPricingSectionProps = {
  /** Section title (signup passes `marketing.signup.pricingTitle`). */
  title?: string;
  /**
   * `full` — public checkout (new clinic registration).
   * `catalog_only` — price showcase for an existing organization (no pay buttons: those create a new signup intent).
   */
  mode?: "full" | "catalog_only";
  /** On /signup: false until consents — plans stay visible, payment is off. */
  checkoutEnabled?: boolean;
};

type CatalogLoadState = "loading" | "ready" | "error";

function buildOptionMap(rows: PublicCatalogOption[]): Map<string, PublicCatalogOption> {
  const m = new Map<string, PublicCatalogOption>();
  for (const r of rows) {
    m.set(r.entitlement_key, r);
  }
  return m;
}

function resolveFeatureLabels(
  keys: string[] | undefined,
  optionMap: Map<string, PublicCatalogOption>,
): { key: string; label: string; hint?: string | null }[] {
  const list = keys ?? [];
  return list.map((key) => {
    const o = optionMap.get(key);
    const overlay = labelForEntitlementKey(key);
    const fromCatalog = o?.display_name?.trim() || key;
    return {
      key,
      label: overlay.title !== key ? overlay.title : fromCatalog,
      hint: overlay.title !== key ? overlay.hint : o?.description?.trim() || null,
    };
  });
}

function catalogOptionTitle(o: PublicCatalogOption): string {
  const overlay = labelForEntitlementKey(o.entitlement_key);
  if (overlay.title !== o.entitlement_key) return overlay.title;
  return o.display_name?.trim() || o.entitlement_key;
}

function checkoutErrorFromCode(code: string, fallback: string): string {
  if (!code) return fallback;
  const key = `checkout.errors.${code}`;
  const translated = tNs("marketing", key);
  return translated === key ? fallback : translated;
}

/**
 * Public plan + options catalog (GET …/catalog/plans, GET …/catalog/options) and checkout (POST …/signup/checkout).
 * Overlay headlines/badges/option titles follow `ui.locale` via settings entitlements + marketing plan copy. Unknown keys keep API `display_name`.
 */
export function PlatformPricingSection({
  title,
  mode = "full",
  checkoutEnabled = true,
}: PlatformPricingSectionProps) {
  const { t, i18n } = useTranslation("marketing");
  const [enterpriseOpened, { open: openEnterprise, close: closeEnterprise }] = useDisclosure(false);
  const resolvedTitle =
    title ?? (mode === "catalog_only" ? t("checkout.titleCatalog") : t("checkout.titleFull"));
  const catalogOnly = mode === "catalog_only";
  const [catalogState, setCatalogState] = useState<CatalogLoadState>("loading");
  const [catalogErr, setCatalogErr] = useState<string | null>(null);
  const [plans, setPlans] = useState<PublicPlanRow[]>([]);
  const [optionMap, setOptionMap] = useState<Map<string, PublicCatalogOption>>(() => new Map());
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [signupEmail, setSignupEmail] = useState("");
  const [checkoutErr, setCheckoutErr] = useState<string | null>(null);
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [turnstileSiteKey, setTurnstileSiteKey] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [extraSelectedKeys, setExtraSelectedKeys] = useState<string[]>([]);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "annual">("monthly");

  const selectedPlan = useMemo(
    () => plans.find((p) => p.slug === selectedSlug) ?? null,
    [plans, selectedSlug],
  );

  const featureRows = useMemo(
    () => resolveFeatureLabels(selectedPlan?.option_keys, optionMap),
    [selectedPlan?.option_keys, optionMap],
  );

  const selectedCopy = useMemo(() => {
    if (!selectedPlan || !isMarketingPlanSlug(selectedPlan.slug)) return null;
    return marketingPlanCopy(selectedPlan.slug);
  }, [selectedPlan, i18n.language]);

  const planIncludedKeys = useMemo(() => {
    const keys = selectedPlan?.option_keys ?? [];
    return new Set(keys.map((k) => String(k).trim()).filter(Boolean));
  }, [selectedPlan?.option_keys]);

  const addonOptions = useMemo(() => {
    const rows = [...optionMap.values()].filter((o) => {
      if (planIncludedKeys.has(o.entitlement_key)) return false;
      if (o.list_price_rub == null || o.list_price_rub === "") return false;
      return parseCatalogAmount(o.list_price_rub) != null;
    });
    const loc = i18n.language.startsWith("ru") ? "ru" : "en";
    rows.sort((a, b) => a.display_name.localeCompare(b.display_name, loc));
    return rows;
  }, [optionMap, planIncludedKeys, i18n.language]);

  const totalsPreview = useMemo(() => {
    if (!selectedPlan) return { monthly: null as number | null, annual: null as number | null };
    const baseM = parseCatalogAmount(selectedPlan.price_monthly_rub ?? null);
    const baseA = parseCatalogAmount(selectedPlan.price_annual_rub ?? null);
    let addM = 0;
    for (const k of extraSelectedKeys) {
      const o = optionMap.get(k);
      const p = o ? parseCatalogAmount(o.list_price_rub) : null;
      if (p != null) addM += p;
    }
    return {
      monthly: baseM != null ? baseM + addM : null,
      annual: baseA != null ? baseA + addM * 12 : null,
    };
  }, [selectedPlan, extraSelectedKeys, optionMap]);

  useEffect(() => {
    setExtraSelectedKeys([]);
    setBillingPeriod("monthly");
  }, [selectedSlug]);

  useEffect(() => {
    const abort = new AbortController();
    setCatalogState("loading");
    setCatalogErr(null);

    const headers = { "X-Request-Id": newOutboundRequestId() };

    const loadOptions = async (): Promise<PublicCatalogOption[]> => {
      const r = await fetch(`${API_BASE}/v1/public/platform/catalog/options`, {
        headers,
        signal: abort.signal,
      });
      const text = await r.text().catch(() => "");
      if (!r.ok) {
        throw new Error(catalogFetchErrorMessage(r.status, text));
      }
      try {
        const data = text ? (JSON.parse(text) as unknown) : [];
        return Array.isArray(data) ? (data as PublicCatalogOption[]) : [];
      } catch (err: unknown) {
        console.error("public_catalog_options_parse_failed", {
          message: err instanceof Error ? err.message : String(err),
        });
        throw new Error(tNs("marketing", "checkout.catalogParseFailed"), { cause: err });
      }
    };

    void (async () => {
      try {
        const r = await fetch(`${API_BASE}/v1/public/platform/catalog/plans`, {
          headers,
          signal: abort.signal,
        });
        const text = await r.text().catch(() => "");
        if (!r.ok) {
          throw new Error(catalogFetchErrorMessage(r.status, text));
        }
        let plansData: unknown = [];
        try {
          plansData = text ? JSON.parse(text) : [];
        } catch (err: unknown) {
          console.error("public_catalog_plans_parse_failed", {
            message: err instanceof Error ? err.message : String(err),
          });
          throw new Error(tNs("marketing", "checkout.catalogParseFailed"), { cause: err });
        }
        const optRows = await loadOptions();
        if (abort.signal.aborted) return;
        const planRows = Array.isArray(plansData) ? (plansData as PublicPlanRow[]) : [];
        const sorted = sortPublicPlanRowsByMarketingOrder(planRows);
        setPlans(sorted);
        setOptionMap(buildOptionMap(optRows));
        setSelectedSlug(sorted.find((p) => p.slug === "growth")?.slug ?? sorted[0]?.slug ?? null);
        setCatalogState("ready");
      } catch (err: unknown) {
        if (abort.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;
        setPlans([]);
        setOptionMap(new Map());
        setSelectedSlug(null);
        const fallback = tNs("marketing", "checkout.catalogLoadFailed");
        setCatalogErr(err instanceof Error && err.message.trim() ? err.message : fallback);
        setCatalogState("error");
      }
    })();

    return () => {
      abort.abort();
    };
  }, []);

  const startCheckout = useCallback(
    async (planSlug: string, period: "monthly" | "annual", tokenOverride: string | null) => {
      setCheckoutErr(null);
      if (!checkoutEnabled) {
        setCheckoutErr(t("checkout.needConsents"));
        return;
      }
      const em = signupEmail.trim();
      if (!em) {
        setCheckoutErr(t("checkout.needEmail"));
        return;
      }
      setCheckoutBusy(true);
      try {
        const body: Record<string, unknown> = {
          email: em,
          plan_slug: planSlug,
          billing_period: period,
          extra_entitlement_keys: extraSelectedKeys,
        };
        const captcha = tokenOverride?.trim();
        if (captcha) body.turnstile_token = captcha;

        const r = await fetch(`${API_BASE}/v1/public/platform/signup/checkout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Request-Id": newOutboundRequestId(),
          },
          body: JSON.stringify(body),
        });
        const data = (await r.json().catch(() => ({}))) as Record<string, unknown>;
        if (!r.ok) {
          const parsed = parsePublicCheckoutFailure(r.status, data);
          const shown = checkoutErrorFromCode(parsed.code, parsed.message);
          if (parsed.code === "captcha_required" && parsed.siteKey) {
            setTurnstileSiteKey(parsed.siteKey);
            setTurnstileToken(null);
            setCheckoutErr(shown);
            return;
          }
          setTurnstileSiteKey(null);
          setTurnstileToken(null);
          setCheckoutErr(shown);
          return;
        }
        setTurnstileSiteKey(null);
        setTurnstileToken(null);
        const url = typeof data.payment_url === "string" ? data.payment_url : "";
        if (url) {
          window.location.href = url;
          return;
        }
        setCheckoutErr(t("checkout.missingPaymentUrl"));
      } catch (err: unknown) {
        console.error("platform checkout request failed", err);
        setCheckoutErr(t("checkout.network"));
      } finally {
        setCheckoutBusy(false);
      }
    },
    [signupEmail, extraSelectedKeys, checkoutEnabled, t],
  );

  const payWithOptionalCaptcha = useCallback(
    (planSlug: string, period: "monthly" | "annual") => {
      const tok = turnstileSiteKey ? turnstileToken : null;
      if (!checkoutEnabled) {
        setCheckoutErr(t("checkout.needConsents"));
        return;
      }
      if (turnstileSiteKey && !tok?.trim()) {
        setCheckoutErr(t("checkout.turnstilePay"));
        return;
      }
      void startCheckout(planSlug, period, tok);
    },
    [turnstileSiteKey, turnstileToken, startCheckout, checkoutEnabled, t],
  );

  const onTurnstileToken = useCallback((token: string) => {
    setTurnstileToken(token);
  }, []);

  const canMonthly = Boolean(
    selectedPlan?.price_monthly_rub != null && selectedPlan.price_monthly_rub !== "",
  );
  const canAnnual = Boolean(
    selectedPlan?.price_annual_rub != null && selectedPlan.price_annual_rub !== "",
  );

  useEffect(() => {
    if (!selectedPlan) return;
    if (!canMonthly && canAnnual) setBillingPeriod("annual");
    if (canMonthly && !canAnnual) setBillingPeriod("monthly");
  }, [selectedPlan, canMonthly, canAnnual]);

  const periodSegmentData = useMemo(() => {
    const rows: { value: string; label: string }[] = [];
    if (canMonthly) rows.push({ value: "monthly", label: t("checkout.periodMonthly") });
    if (canAnnual) rows.push({ value: "annual", label: t("checkout.periodAnnual") });
    return rows;
  }, [canMonthly, canAnnual, t]);

  const periodAllowed = billingPeriod === "monthly" ? canMonthly : canAnnual;

  const compositionName = selectedCopy?.headline ?? selectedPlan?.display_name ?? "";

  const planDetailsPaper = selectedPlan ? (
    <Paper
      p="xl"
      radius="lg"
      withBorder
      shadow="none"
      style={{ background: "color-mix(in srgb, var(--mantine-color-slate-0) 40%, var(--bg-card))" }}
    >
      <Stack gap="sm">
        <Text fw={600} size="sm">
          {t("checkout.composition", { name: compositionName })}
        </Text>
        {selectedCopy?.bullets?.length ? (
          <List size="sm" spacing={4} c="dimmed">
            {selectedCopy.bullets.map((line) => (
              <List.Item key={line}>
                <Text span fw={500} c="var(--text-main)">
                  {line}
                </Text>
              </List.Item>
            ))}
          </List>
        ) : featureRows.length === 0 ? (
          <Text size="sm" c="dimmed">
            {t("checkout.compositionUnknown")}
          </Text>
        ) : (
          <List size="sm" spacing={4} c="dimmed">
            {featureRows.map((f) => (
              <List.Item key={f.key}>
                <Text span fw={500} c="var(--text-main)">
                  {f.label}
                </Text>
                {f.hint ? (
                  <Text size="xs" c="dimmed" mt={2}>
                    {f.hint}
                  </Text>
                ) : null}
              </List.Item>
            ))}
          </List>
        )}
      </Stack>
    </Paper>
  ) : null;

  const addonsPaper =
    !catalogOnly && selectedPlan && addonOptions.length > 0 ? (
      <Paper p="xl" radius="lg" withBorder shadow="none">
        <Stack gap="sm">
          <Text fw={600} size="sm">
            {t("checkout.addonsTitle")}
          </Text>
          <Text size="xs" c="dimmed">
            {t("checkout.addonsHint")}
          </Text>
          <Stack gap="xs">
            {addonOptions.map((o) => {
              const price = parseCatalogAmount(o.list_price_rub);
              return (
                <Checkbox
                  key={o.entitlement_key}
                  checked={extraSelectedKeys.includes(o.entitlement_key)}
                  onChange={() => {
                    setExtraSelectedKeys((prev) =>
                      prev.includes(o.entitlement_key)
                        ? prev.filter((x) => x !== o.entitlement_key)
                        : [...prev, o.entitlement_key],
                    );
                  }}
                  label={
                    <Stack gap={0}>
                      <Text size="sm" fw={500}>
                        {catalogOptionTitle(o)}
                      </Text>
                      {price != null ? (
                        <Text size="xs" c="dimmed">
                          {t("checkout.addonPrice", {
                            price: formatCatalogUsdLabel(price) ?? "",
                          })}
                        </Text>
                      ) : null}
                    </Stack>
                  }
                />
              );
            })}
          </Stack>
        </Stack>
      </Paper>
    ) : null;

  const enterpriseBullets = [0, 1, 2].map((i) => tNs("marketing", `enterprise.bullets.${i}`));

  return (
    <>
      <EnterpriseLeadModal opened={enterpriseOpened} onClose={closeEnterprise} />
      <Stack gap="xl">
        {catalogState === "loading" ? (
          <Text size="sm" c="dimmed">
            {t("checkout.loading")}
          </Text>
        ) : null}
        {catalogState === "error" && catalogErr ? (
          <Alert color="red" variant="light" title={t("checkout.catalogUnavailableTitle")}>
            {catalogErr}
          </Alert>
        ) : null}
        {catalogState === "ready" && plans.length === 0 ? (
          <Alert color="gray" variant="light" title={t("checkout.emptyTitle")}>
            {t("checkout.emptyBody")}
          </Alert>
        ) : null}

        <Paper p="xl" radius="lg" withBorder shadow="sm" style={{ background: "var(--bg-card)" }}>
          <div>
            <Title order={3} style={{ color: "var(--text-main)" }}>
              {resolvedTitle}
            </Title>
            {!catalogOnly ? (
              <Text size="sm" c="dimmed" mt={6}>
                {t("checkout.lead")}
              </Text>
            ) : (
              <Alert color="blue" variant="light" title={t("checkout.upgradeHintTitle")} mt="sm">
                {t("checkout.upgradeHint")}
              </Alert>
            )}
          </div>
        </Paper>

        {catalogState === "ready" && plans.length > 0 ? (
          <>
            <Paper
              p="xl"
              radius="lg"
              withBorder
              shadow="none"
              style={{ background: "var(--bg-card)", border: "1px solid var(--divider)" }}
            >
              <Stack gap="lg">
                <Grid gutter="md">
                  {plans.map((p) => {
                    const selected = p.slug === selectedSlug;
                    const meta = marketingOverlayForSlug(p.slug);
                    const copy = isMarketingPlanSlug(p.slug) ? marketingPlanCopy(p.slug) : null;
                    const cardTitle = copy?.headline ?? p.display_name;
                    const subtitle = copy?.badge ?? p.description;
                    const featured = Boolean(meta?.featured);
                    const monthlyLabel =
                      formatCatalogUsdLabel(p.price_monthly_rub) ?? `${p.price_monthly_rub ?? "—"}`;
                    const annualLabel =
                      p.price_annual_rub != null && p.price_annual_rub !== ""
                        ? formatCatalogUsdLabel(p.price_annual_rub) ?? `${p.price_annual_rub}`
                        : null;
                    return (
                      <Grid.Col
                        key={p.slug}
                        span={{ base: 12, sm: 6, md: 4 }}
                        style={{ display: "flex", alignItems: "stretch" }}
                      >
                        <Card
                          withBorder
                          padding="lg"
                          radius="lg"
                          style={{
                            flex: 1,
                            minHeight: 248,
                            display: "flex",
                            flexDirection: "column",
                            cursor: "pointer",
                            borderWidth: featured || selected ? 2 : 1,
                            borderColor: selected
                              ? "var(--mantine-color-slate-7)"
                              : featured
                                ? "var(--mantine-color-slate-6)"
                                : undefined,
                            boxShadow: selected || featured ? "var(--mantine-shadow-sm)" : undefined,
                            background: featured
                              ? "linear-gradient(180deg, #ffffff 0%, color-mix(in srgb, var(--mantine-color-slate-0) 55%, #ffffff) 100%)"
                              : undefined,
                          }}
                          onClick={() => setSelectedSlug(p.slug)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setSelectedSlug(p.slug);
                            }
                          }}
                          tabIndex={0}
                          role="button"
                          aria-pressed={selected}
                          aria-label={t("checkout.planAria", { name: cardTitle })}
                        >
                          <Stack gap={6} justify="space-between" style={{ flex: 1 }}>
                            <Stack gap={6}>
                              {featured ? (
                                <Text size="xs" fw={700} tt="uppercase" c="teal.7" lts={0.6}>
                                  {t("pricing.recommended")}
                                </Text>
                              ) : null}
                              <Text fw={700} style={{ color: "var(--text-main)" }}>
                                {cardTitle}
                              </Text>
                              {subtitle ? (
                                <Text size="xs" c="dimmed" lineClamp={4} style={{ minHeight: "3.25rem" }}>
                                  {subtitle}
                                </Text>
                              ) : (
                                <Box style={{ minHeight: "3.25rem" }} />
                              )}
                            </Stack>
                            <Stack gap={4} mt="auto">
                              {p.price_monthly_rub != null && p.price_monthly_rub !== "" ? (
                                <Text size="sm" fw={600}>
                                  {monthlyLabel} {t("checkout.perMonth")}
                                </Text>
                              ) : null}
                              {annualLabel ? (
                                <Text size="sm" c="dimmed">
                                  {annualLabel} {t("checkout.perYear")}
                                </Text>
                              ) : null}
                            </Stack>
                          </Stack>
                        </Card>
                      </Grid.Col>
                    );
                  })}
                </Grid>

                <Paper
                  p="lg"
                  radius="lg"
                  withBorder
                  style={{
                    borderStyle: "dashed",
                    background: "var(--bg-card)",
                  }}
                >
                  <Group justify="space-between" align="flex-start" wrap="wrap" gap="md">
                    <Stack gap="xs" maw={560}>
                      <Text fw={700} style={{ color: "var(--text-main)" }}>
                        {t("enterprise.headline")}
                      </Text>
                      <Text size="sm" fw={600} c="var(--text-main)">
                        {t("enterprise.priceHint")} · {t("enterprise.priceLabel")}
                      </Text>
                      <List size="sm" spacing={4} c="dimmed">
                        {enterpriseBullets.map((line) => (
                          <List.Item key={line}>{line}</List.Item>
                        ))}
                      </List>
                    </Stack>
                    <Button variant="outline" color="slate" size="sm" onClick={openEnterprise}>
                      {t("pricing.discuss")}
                    </Button>
                  </Group>
                </Paper>
              </Stack>
            </Paper>

            {catalogOnly && selectedPlan ? <Stack gap="md">{planDetailsPaper}</Stack> : null}

            {!catalogOnly && selectedPlan ? (
              <Grid gutter="xl" align="flex-start">
                <Grid.Col span={{ base: 12, md: 7 }}>
                  <Stack gap="md">
                    {planDetailsPaper}
                    {addonsPaper}
                  </Stack>
                </Grid.Col>
                <Grid.Col span={{ base: 12, md: 5 }}>
                  <Box
                    style={{
                      position: "sticky",
                      top: 24,
                      alignSelf: "flex-start",
                    }}
                  >
                    <Paper
                      p="xl"
                      radius="lg"
                      shadow="xl"
                      withBorder
                      style={{
                        background: "var(--bg-card)",
                        border: "1px solid var(--mantine-color-gray-3)",
                        boxShadow: "var(--mantine-shadow-xl)",
                      }}
                    >
                      {!checkoutEnabled ? (
                        <Alert color="gray" variant="light" title={t("checkout.checkoutDisabledTitle")} mb="lg">
                          {t("checkout.checkoutDisabledBody")}
                        </Alert>
                      ) : null}
                      <Title order={4} mb="md" style={{ color: "var(--text-main)" }}>
                        {t("checkout.dueTitle")}
                      </Title>
                      {totalsPreview.monthly != null || totalsPreview.annual != null ? (
                        <Stack gap={4} mb="lg">
                          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                            {t("checkout.total")}
                          </Text>
                          {billingPeriod === "monthly" && totalsPreview.monthly != null ? (
                            <Text fz={28} fw={800} style={{ color: "var(--text-main)", letterSpacing: "-0.02em" }}>
                              {formatCatalogUsdLabel(totalsPreview.monthly)}{" "}
                              <Text span fz="md" fw={600}>
                                {t("checkout.perMonth")}
                              </Text>
                            </Text>
                          ) : null}
                          {billingPeriod === "annual" && totalsPreview.annual != null ? (
                            <Text fz={28} fw={800} style={{ color: "var(--text-main)", letterSpacing: "-0.02em" }}>
                              {formatCatalogUsdLabel(totalsPreview.annual)}{" "}
                              <Text span fz="md" fw={600}>
                                {t("checkout.perYear")}
                              </Text>
                            </Text>
                          ) : null}
                          {totalsPreview.monthly != null && totalsPreview.annual != null ? (
                            <Text size="sm" c="dimmed">
                              {billingPeriod === "monthly"
                                ? t("checkout.annualAlternative", {
                                    amount: formatCatalogUsdLabel(totalsPreview.annual) ?? "",
                                  })
                                : t("checkout.monthlyAlternative", {
                                    amount: formatCatalogUsdLabel(totalsPreview.monthly) ?? "",
                                  })}
                            </Text>
                          ) : null}
                        </Stack>
                      ) : null}

                      {periodSegmentData.length > 1 ? (
                        <SegmentedControl
                          value={billingPeriod}
                          onChange={(v) => setBillingPeriod(v as "monthly" | "annual")}
                          data={periodSegmentData}
                          fullWidth
                          mb="md"
                          disabled={!checkoutEnabled}
                          color="slate"
                        />
                      ) : null}

                      <TextInput
                        label={t("checkout.emailLabel")}
                        placeholder="owner@company.example"
                        value={signupEmail}
                        onChange={(e) => setSignupEmail(e.currentTarget.value)}
                        type="email"
                        autoComplete="email"
                        disabled={!checkoutEnabled}
                        mb="sm"
                      />

                      {turnstileSiteKey ? (
                        <Stack gap="xs" mb="sm">
                          <Text size="sm" fw={500}>
                            {t("lead.captchaTitle")}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {t("checkout.captchaHintPay")}
                          </Text>
                          <TurnstileWidget
                            siteKey={turnstileSiteKey}
                            onToken={onTurnstileToken}
                            onExpire={() => setTurnstileToken(null)}
                          />
                        </Stack>
                      ) : null}

                      {checkoutErr ? (
                        <Text size="sm" c="red" mb="sm">
                          {checkoutErr}
                        </Text>
                      ) : null}

                      <Button
                        size="lg"
                        fullWidth
                        radius="md"
                        loading={checkoutBusy}
                        disabled={!checkoutEnabled || !periodAllowed || checkoutBusy || !signupEmail.trim()}
                        onClick={() => payWithOptionalCaptcha(selectedPlan.slug, billingPeriod)}
                      >
                        {t("checkout.subscribe")}
                      </Button>
                    </Paper>
                  </Box>
                </Grid.Col>
              </Grid>
            ) : null}
          </>
        ) : null}
      </Stack>
    </>
  );
}
