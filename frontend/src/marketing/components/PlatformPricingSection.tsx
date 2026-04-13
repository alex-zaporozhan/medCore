import { API_BASE, newOutboundRequestId, parseFastApiErrorBody } from "@/api/client";
import { EnterpriseLeadModal } from "@/marketing/components/EnterpriseLeadModal";
import {
  ENTERPRISE_PLAN_MARKETING,
  formatMonthlyRubLabel,
  marketingOverlayForSlug,
  sortPublicPlanRowsByMarketingOrder,
} from "@/marketing/marketingPublicPlans";
import { parsePublicCheckoutFailure } from "@/marketing/platformBillingPublic";
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
import { TurnstileWidget } from "./TurnstileWidget";

export type PublicPlanRow = {
  slug: string;
  display_name: string;
  description?: string | null;
  option_keys?: string[];
  price_monthly_rub?: string | null;
  price_annual_rub?: string | null;
};

export type PublicCatalogOption = {
  entitlement_key: string;
  display_name: string;
  description?: string | null;
  list_price_rub?: string | null;
};

type PlatformPricingSectionProps = {
  /** Заголовок секции (например «Тарифы» на /pricing vs встроенный блок на лендинге). */
  title?: string;
  /**
   * `full` — публичный checkout (новая регистрация клиники).
   * `catalog_only` — только витрина цен для существующей организации (без кнопок оплаты: иначе создаётся новый signup intent).
   */
  mode?: "full" | "catalog_only";
  /** На /signup: false до согласий — тарифы видны, оплата отключена. */
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

function parseRubAmount(s: string | null | undefined): number | null {
  if (s == null || s === "") return null;
  const n = Number.parseFloat(String(s).replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function resolveFeatureLabels(
  keys: string[] | undefined,
  optionMap: Map<string, PublicCatalogOption>,
): { key: string; label: string; hint?: string | null }[] {
  const list = keys ?? [];
  return list.map((key) => {
    const o = optionMap.get(key);
    return {
      key,
      label: o?.display_name?.trim() || key,
      hint: o?.description?.trim() || null,
    };
  });
}

/**
 * Публичный каталог планов + опций (GET …/catalog/plans, GET …/catalog/options) и checkout (POST …/signup/checkout).
 * Режим «конструктора»: выбор базового плана из каталога; состав модулей подтягивается из `option_keys` плана
 * и подписей из справочника опций (человекочитаемо, без внутренних ключей в интерфейсе).
 */
export function PlatformPricingSection({
  title,
  mode = "full",
  checkoutEnabled = true,
}: PlatformPricingSectionProps) {
  const [enterpriseOpened, { open: openEnterprise, close: closeEnterprise }] = useDisclosure(false);
  const resolvedTitle =
    title ??
    (mode === "catalog_only" ? "Каталог тарифов (справочно)" : "Подбор тарифа и оформление");
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

  const selectedMarketing = useMemo(
    () => marketingOverlayForSlug(selectedPlan?.slug),
    [selectedPlan?.slug],
  );

  const planIncludedKeys = useMemo(() => {
    const keys = selectedPlan?.option_keys ?? [];
    return new Set(keys.map((k) => String(k).trim()).filter(Boolean));
  }, [selectedPlan?.option_keys]);

  const addonOptions = useMemo(() => {
    const rows = [...optionMap.values()].filter((o) => {
      if (planIncludedKeys.has(o.entitlement_key)) return false;
      if (o.list_price_rub == null || o.list_price_rub === "") return false;
      return parseRubAmount(o.list_price_rub) != null;
    });
    rows.sort((a, b) => a.display_name.localeCompare(b.display_name, "ru"));
    return rows;
  }, [optionMap, planIncludedKeys]);

  const totalsPreview = useMemo(() => {
    if (!selectedPlan) return { monthly: null as number | null, annual: null as number | null };
    const baseM = parseRubAmount(selectedPlan.price_monthly_rub ?? null);
    const baseA = parseRubAmount(selectedPlan.price_annual_rub ?? null);
    let addM = 0;
    for (const k of extraSelectedKeys) {
      const o = optionMap.get(k);
      const p = o ? parseRubAmount(o.list_price_rub) : null;
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
    let cancelled = false;
    setCatalogState("loading");
    setCatalogErr(null);

    const headers = { "X-Request-Id": newOutboundRequestId() };

    const loadOptions = async (): Promise<PublicCatalogOption[]> => {
      const r = await fetch(`${API_BASE}/v1/public/platform/catalog/options`, { headers });
      const text = await r.text().catch(() => "");
      if (!r.ok) return [];
      try {
        const data = text ? (JSON.parse(text) as unknown) : [];
        return Array.isArray(data) ? (data as PublicCatalogOption[]) : [];
      } catch {
        return [];
      }
    };

    void (async () => {
      try {
        const r = await fetch(`${API_BASE}/v1/public/platform/catalog/plans`, { headers });
        const text = await r.text().catch(() => "");
        if (!r.ok) {
          const parsed = parseFastApiErrorBody(text || "{}");
          throw new Error(parsed.rawMessage?.trim() || `Ошибка ${r.status}`);
        }
        let plansData: unknown = [];
        try {
          plansData = text ? JSON.parse(text) : [];
        } catch {
          throw new Error("Некорректный ответ каталога планов");
        }
        const optRows = await loadOptions();
        if (cancelled) return;
        const planRows = Array.isArray(plansData) ? (plansData as PublicPlanRow[]) : [];
        const sorted = sortPublicPlanRowsByMarketingOrder(planRows);
        setPlans(sorted);
        setOptionMap(buildOptionMap(optRows));
        setSelectedSlug(sorted.find((p) => p.slug === "growth")?.slug ?? sorted[0]?.slug ?? null);
        setCatalogState("ready");
      } catch {
        if (cancelled) return;
        setPlans([]);
        setOptionMap(new Map());
        setSelectedSlug(null);
        setCatalogErr(
          "Не удалось загрузить каталог планов. Проверьте соединение с сервером и обновите страницу.",
        );
        setCatalogState("error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const startCheckout = useCallback(
    async (planSlug: string, period: "monthly" | "annual", tokenOverride: string | null) => {
      setCheckoutErr(null);
      if (!checkoutEnabled) {
        setCheckoutErr("Отметьте оба согласия выше, чтобы перейти к оплате.");
        return;
      }
      const em = signupEmail.trim();
      if (!em) {
        setCheckoutErr("Укажите email владельца — на него придёт приглашение в админку после оплаты.");
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
        const t = tokenOverride?.trim();
        if (t) body.turnstile_token = t;

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
          if (parsed.code === "captcha_required" && parsed.siteKey) {
            setTurnstileSiteKey(parsed.siteKey);
            setTurnstileToken(null);
            setCheckoutErr(parsed.message);
            return;
          }
          setTurnstileSiteKey(null);
          setTurnstileToken(null);
          setCheckoutErr(parsed.message);
          return;
        }
        setTurnstileSiteKey(null);
        setTurnstileToken(null);
        const url = typeof data.payment_url === "string" ? data.payment_url : "";
        if (url) window.location.href = url;
      } finally {
        setCheckoutBusy(false);
      }
    },
    [signupEmail, extraSelectedKeys, checkoutEnabled],
  );

  const payWithOptionalCaptcha = useCallback(
    (planSlug: string, period: "monthly" | "annual") => {
      const tok = turnstileSiteKey ? turnstileToken : null;
      if (!checkoutEnabled) {
        setCheckoutErr("Отметьте оба согласия выше, чтобы перейти к оплате.");
        return;
      }
      if (turnstileSiteKey && !tok?.trim()) {
        setCheckoutErr("Сначала пройдите проверку Turnstile, затем снова нажмите «Оформить подписку».");
        return;
      }
      void startCheckout(planSlug, period, tok);
    },
    [turnstileSiteKey, turnstileToken, startCheckout, checkoutEnabled],
  );

  const onTurnstileToken = useCallback((t: string) => {
    setTurnstileToken(t);
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
    if (canMonthly) rows.push({ value: "monthly", label: "Ежемесячно" });
    if (canAnnual) rows.push({ value: "annual", label: "Ежегодно" });
    return rows;
  }, [canMonthly, canAnnual]);

  const periodAllowed = billingPeriod === "monthly" ? canMonthly : canAnnual;

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
          Состав выбранного плана «{selectedMarketing?.headline ?? selectedPlan.display_name}»
        </Text>
        {selectedMarketing?.bullets?.length ? (
          <List size="sm" spacing={4} c="dimmed">
            {selectedMarketing.bullets.map((line) => (
              <List.Item key={line}>
                <Text span fw={500} c="var(--text-main)">
                  {line}
                </Text>
              </List.Item>
            ))}
          </List>
        ) : featureRows.length === 0 ? (
          <Text size="sm" c="dimmed">
            Состав модулей уточняется у оператора платформы.
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
            Дополнительные модули (к корзине)
          </Text>
          <Text size="xs" c="dimmed">
            Цены дополнений — помесячные: при годовой подписке они умножаются на 12 и добавляются к годовой цене
            плана.
          </Text>
          <Stack gap="xs">
            {addonOptions.map((o) => {
              const price = parseRubAmount(o.list_price_rub);
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
                        {o.display_name}
                      </Text>
                      {price != null ? (
                        <Text size="xs" c="dimmed">
                          +{price.toLocaleString("ru-RU")} ₽ / мес
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

  return (
    <>
      <EnterpriseLeadModal opened={enterpriseOpened} onClose={closeEnterprise} />
      <Stack gap="xl">
        {catalogState === "loading" ? (
          <Text size="sm" c="dimmed">
            Загрузка каталога…
          </Text>
        ) : null}
        {catalogState === "error" && catalogErr ? (
          <Alert color="red" variant="light" title="Каталог недоступен">
            {catalogErr}
          </Alert>
        ) : null}
        {catalogState === "ready" && plans.length === 0 ? (
          <Alert color="gray" variant="light" title="Нет планов">
            В каталоге пока нет доступных тарифов. Обратитесь к оператору платформы.
          </Alert>
        ) : null}

        <Paper p="xl" radius="lg" withBorder shadow="sm" style={{ background: "var(--bg-card)" }}>
          <div>
            <Title order={3} style={{ color: "var(--text-main)" }}>
              {resolvedTitle}
            </Title>
            {!catalogOnly ? (
              <Text size="sm" c="dimmed" mt={6}>
                Выберите план и при необходимости отметьте дополнительные модули — сумма пересчитывается автоматически.
                Оплата — через ЮKassa.
              </Text>
            ) : (
              <Alert color="blue" variant="light" title="Как сменить тариф" mt="sm">
                Онлайн-оплата на публичной странице создаёт{" "}
                <Text span fw={600}>
                  новую
                </Text>{" "}
                регистрацию организации. Для апгрейда у действующего клиента используйте раздел подписки в админке или
                свяжитесь с оператором платформы.
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
                    const m = marketingOverlayForSlug(p.slug);
                    const cardTitle = m?.headline ?? p.display_name;
                    const subtitle = m?.badge ?? p.description;
                    const featured = Boolean(m?.featured);
                    const monthlyLabel =
                      formatMonthlyRubLabel(p.price_monthly_rub) ?? `${p.price_monthly_rub ?? "—"} ₽`;
                    const annualLabel =
                      p.price_annual_rub != null && p.price_annual_rub !== ""
                        ? formatMonthlyRubLabel(p.price_annual_rub) ?? `${p.price_annual_rub} ₽`
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
                          aria-label={`Тариф ${cardTitle}`}
                        >
                          <Stack gap={6} justify="space-between" style={{ flex: 1 }}>
                            <Stack gap={6}>
                              {featured ? (
                                <Text size="xs" fw={700} tt="uppercase" c="teal.7" lts={0.6}>
                                  Рекомендуем
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
                                  {monthlyLabel} / мес
                                </Text>
                              ) : null}
                              {annualLabel ? (
                                <Text size="sm" c="dimmed">
                                  {annualLabel} / год
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
                        {ENTERPRISE_PLAN_MARKETING.headline}
                      </Text>
                      <Text size="sm" fw={600} c="var(--text-main)">
                        {ENTERPRISE_PLAN_MARKETING.priceHint} · {ENTERPRISE_PLAN_MARKETING.priceLabel}
                      </Text>
                      <List size="sm" spacing={4} c="dimmed">
                        {ENTERPRISE_PLAN_MARKETING.bullets.map((line) => (
                          <List.Item key={line}>{line}</List.Item>
                        ))}
                      </List>
                    </Stack>
                    <Button variant="outline" color="slate" size="sm" onClick={openEnterprise}>
                      Обсудить внедрение
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
                        <Alert color="gray" variant="light" title="Оплата недоступна" mb="lg">
                          Отметьте оба согласия на странице регистрации, чтобы активировать кнопку оплаты.
                        </Alert>
                      ) : null}
                      <Title order={4} mb="md" style={{ color: "var(--text-main)" }}>
                        К оплате
                      </Title>
                      {totalsPreview.monthly != null || totalsPreview.annual != null ? (
                        <Stack gap={4} mb="lg">
                          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                            Итого
                          </Text>
                          {billingPeriod === "monthly" && totalsPreview.monthly != null ? (
                            <Text fz={28} fw={800} style={{ color: "var(--text-main)", letterSpacing: "-0.02em" }}>
                              {totalsPreview.monthly.toLocaleString("ru-RU", {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 2,
                              })}{" "}
                              ₽ <Text span fz="md" fw={600}> / мес</Text>
                            </Text>
                          ) : null}
                          {billingPeriod === "annual" && totalsPreview.annual != null ? (
                            <Text fz={28} fw={800} style={{ color: "var(--text-main)", letterSpacing: "-0.02em" }}>
                              {totalsPreview.annual.toLocaleString("ru-RU", {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 2,
                              })}{" "}
                              ₽ <Text span fz="md" fw={600}> / год</Text>
                            </Text>
                          ) : null}
                          {totalsPreview.monthly != null && totalsPreview.annual != null ? (
                            <Text size="sm" c="dimmed">
                              {billingPeriod === "monthly"
                                ? `Годовой вариант: ${totalsPreview.annual.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })} ₽ / год`
                                : `Помесячно: ${totalsPreview.monthly.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })} ₽ / мес`}
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
                        label="Email владельца (логин администратора)"
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
                            Проверка антиспама
                          </Text>
                          <Text size="xs" c="dimmed">
                            После проверки снова нажмите «Оформить подписку».
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
                        disabled={
                          !checkoutEnabled || !periodAllowed || checkoutBusy || !signupEmail.trim()
                        }
                        onClick={() => payWithOptionalCaptcha(selectedPlan.slug, billingPeriod)}
                      >
                        Оформить подписку
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
