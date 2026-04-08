import { API_BASE, newOutboundRequestId, parseFastApiErrorBody } from "@/api/client";
import { parsePublicCheckoutFailure } from "@/marketing/platformBillingPublic";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  List,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
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
}: PlatformPricingSectionProps) {
  const resolvedTitle =
    title ??
    (mode === "catalog_only" ? "Каталог тарифов (справочно)" : "Подбор тарифа для клиники");
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

  const selectedPlan = useMemo(
    () => plans.find((p) => p.slug === selectedSlug) ?? null,
    [plans, selectedSlug],
  );

  const featureRows = useMemo(
    () => resolveFeatureLabels(selectedPlan?.option_keys, optionMap),
    [selectedPlan?.option_keys, optionMap],
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
        setPlans(planRows);
        setOptionMap(buildOptionMap(optRows));
        setSelectedSlug(planRows[0]?.slug ?? null);
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
    async (planSlug: string, billingPeriod: "monthly" | "annual", tokenOverride: string | null) => {
      setCheckoutErr(null);
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
          billing_period: billingPeriod,
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
    [signupEmail, extraSelectedKeys],
  );

  const payWithOptionalCaptcha = useCallback(
    (planSlug: string, billingPeriod: "monthly" | "annual") => {
      const tok = turnstileSiteKey ? turnstileToken : null;
      if (turnstileSiteKey && !tok?.trim()) {
        setCheckoutErr("Сначала пройдите проверку Turnstile, затем снова нажмите «Оплатить».");
        return;
      }
      void startCheckout(planSlug, billingPeriod, tok);
    },
    [turnstileSiteKey, turnstileToken, startCheckout],
  );

  const onTurnstileToken = useCallback((t: string) => {
    setTurnstileToken(t);
  }, []);

  return (
    <Paper
      p="xl"
      radius="md"
      shadow="none"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--divider)",
      }}
    >
      <Stack gap="md">
        <div>
          <Title order={3} style={{ color: "var(--text-main)" }}>
            {resolvedTitle}
          </Title>
          {!catalogOnly ? (
            <Text size="sm" c="dimmed" mt={6}>
              Выберите план и при необходимости отметьте дополнительные модули — сумма пересчитывается автоматически.
              Оплата — через YooKassa.
            </Text>
          ) : (
            <Alert color="blue" variant="light" title="Как сменить тариф" mt="sm">
              Онлайн-оплата на публичной странице создаёт{" "}
              <Text span fw={600}>
                новую
              </Text>{" "}
              регистрацию клиники. Для апгрейда у действующей организации используйте раздел подписки в
              админке или свяжитесь с оператором платформы.
            </Alert>
          )}
        </div>

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

        {catalogState === "ready" && plans.length > 0 ? (
          <>
            <Grid gutter="md">
              {plans.map((p) => {
                const selected = p.slug === selectedSlug;
                return (
                  <Grid.Col key={p.slug} span={{ base: 12, sm: 6, md: 4 }}>
                    <Card
                      withBorder
                      padding="md"
                      radius="md"
                      style={{
                        cursor: "pointer",
                        borderColor: selected ? "var(--mantine-color-teal-6)" : undefined,
                        boxShadow: selected ? "var(--mantine-shadow-sm)" : undefined,
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
                      aria-label={`Тариф ${p.display_name}`}
                    >
                      <Stack gap={6}>
                        <Text fw={700} style={{ color: "var(--text-main)" }}>
                          {p.display_name}
                        </Text>
                        {p.description ? (
                          <Text size="xs" c="dimmed" lineClamp={4}>
                            {p.description}
                          </Text>
                        ) : null}
                        {p.price_monthly_rub != null && p.price_monthly_rub !== "" ? (
                          <Text size="sm" fw={600}>
                            {p.price_monthly_rub} ₽ / мес
                          </Text>
                        ) : null}
                        {p.price_annual_rub != null && p.price_annual_rub !== "" ? (
                          <Text size="sm" c="dimmed">
                            {p.price_annual_rub} ₽ / год
                          </Text>
                        ) : null}
                      </Stack>
                    </Card>
                  </Grid.Col>
                );
              })}
            </Grid>

            {selectedPlan ? (
              <Paper
                p="md"
                radius="md"
                withBorder
                style={{ background: "color-mix(in srgb, var(--mantine-color-teal-0) 35%, var(--bg-card))" }}
              >
                <Stack gap="sm">
                  <Text fw={600} size="sm">
                    Состав выбранного плана «{selectedPlan.display_name}»
                  </Text>
                  {featureRows.length === 0 ? (
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
            ) : null}

            {!catalogOnly && selectedPlan && addonOptions.length > 0 ? (
              <Paper p="md" radius="md" withBorder>
                <Stack gap="sm">
                  <Text fw={600} size="sm">
                    Дополнительные модули (к корзине)
                  </Text>
                  <Text size="xs" c="dimmed">
                    Цены дополнений — помесячные: при годовой подписке они умножаются на 12 и добавляются к годовой
                    цене плана.
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
            ) : null}

            {!catalogOnly && selectedPlan &&
            (totalsPreview.monthly != null || totalsPreview.annual != null) ? (
              <Paper p="sm" radius="md" withBorder style={{ borderStyle: "dashed" }}>
                <Text size="sm" fw={600}>
                  Итого к оплате:{" "}
                  {totalsPreview.monthly != null ? (
                    <Text span>
                      {totalsPreview.monthly.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}{" "}
                      ₽ / мес
                    </Text>
                  ) : null}
                  {totalsPreview.monthly != null && totalsPreview.annual != null ? (
                    <Text span c="dimmed" mx={6}>
                      ·
                    </Text>
                  ) : null}
                  {totalsPreview.annual != null ? (
                    <Text span>
                      {totalsPreview.annual.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}{" "}
                      ₽ / год
                    </Text>
                  ) : null}
                </Text>
              </Paper>
            ) : null}

            {!catalogOnly && selectedPlan ? (
              <>
                <TextInput
                  label="Email владельца (логин администратора клиники)"
                  placeholder="owner@clinic.example"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.currentTarget.value)}
                  type="email"
                  autoComplete="email"
                />
                {turnstileSiteKey ? (
                  <Stack gap="xs">
                    <Text size="sm" fw={500}>
                      Проверка антиспама
                    </Text>
                    <Text size="xs" c="dimmed">
                      После успешной проверки снова нажмите «Оплатить» для выбранного периода.
                    </Text>
                    <TurnstileWidget
                      siteKey={turnstileSiteKey}
                      onToken={onTurnstileToken}
                      onExpire={() => setTurnstileToken(null)}
                    />
                  </Stack>
                ) : null}
                {checkoutErr ? (
                  <Text size="sm" c="red">
                    {checkoutErr}
                  </Text>
                ) : null}
                <Group gap="sm" wrap="wrap">
                  <Button
                    size="sm"
                    variant="filled"
                    color="teal"
                    loading={checkoutBusy}
                    disabled={!selectedPlan.price_monthly_rub}
                    onClick={() => payWithOptionalCaptcha(selectedPlan.slug, "monthly")}
                  >
                    Оплатить подписку (месяц)
                  </Button>
                  <Button
                    size="sm"
                    variant="light"
                    color="teal"
                    loading={checkoutBusy}
                    disabled={!selectedPlan.price_annual_rub}
                    onClick={() => payWithOptionalCaptcha(selectedPlan.slug, "annual")}
                  >
                    Оплатить подписку (год)
                  </Button>
                </Group>
              </>
            ) : null}
          </>
        ) : null}
      </Stack>
    </Paper>
  );
}
