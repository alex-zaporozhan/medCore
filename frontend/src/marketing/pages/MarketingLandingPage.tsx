import heroFallbackUrl from "@/assets/marketing/landing-admin-workstation.svg?url";
import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";
import { EnterpriseLeadModal } from "@/marketing/components/EnterpriseLeadModal";
import { LANDING_HERO_PUBLIC_URLS } from "@/marketing/landingPublicAssets";
import { MARKETING_PLAN_ORDER, PUBLIC_PLAN_MARKETING } from "@/marketing/marketingPublicPlans";
import { usePublicCatalogPriceLabels } from "@/marketing/usePublicCatalogPriceLabels";
import { tNs } from "@/i18n";
import { ROUTE_PATHS } from "@/routePaths";
import "@fontsource/plus-jakarta-sans/latin-600.css";
import "@fontsource/plus-jakarta-sans/latin-700.css";
import "@fontsource/plus-jakarta-sans/latin-ext-600.css";
import "@fontsource/plus-jakarta-sans/latin-ext-700.css";
import {
  IconBarbell,
  IconBrandMessenger,
  IconBriefcase,
  IconBuildingBank,
  IconBuildingHospital,
  IconChartLine,
  IconDiscount2,
  IconLayoutDashboard,
  IconLayoutKanban,
  IconListCheck,
  IconRobot,
  IconShieldLock,
} from "@tabler/icons-react";
import {
  Anchor,
  Box,
  Button,
  Container,
  Group,
  List,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { ArrowRight } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import "./marketingLanding.css";

function HeroProductShot({ alt }: { alt: string }) {
  const sources: readonly string[] = [...LANDING_HERO_PUBLIC_URLS, heroFallbackUrl];
  const [attempt, setAttempt] = useState(0);
  const src = sources[Math.min(attempt, sources.length - 1)];
  const isRasterHero = attempt < LANDING_HERO_PUBLIC_URLS.length;

  return (
    <Box className="marketing-hero-pedestal">
      <Box className="marketing-hero-3d marketing-hero-shadow-xl" w="100%" maw={560}>
        <img
          key={src}
          src={src}
          alt={alt}
          className="marketing-hero-shot"
          width={960}
          height={600}
          sizes="(max-width: 48em) 100vw, 560px"
          loading="eager"
          decoding="async"
          {...(isRasterHero ? { fetchPriority: "high" as const } : {})}
          onError={() => {
            setAttempt((a) => (a < sources.length - 1 ? a + 1 : a));
          }}
        />
      </Box>
    </Box>
  );
}

export default function MarketingLandingPage() {
  const { t, i18n } = useTranslation("marketing");
  const [enterpriseOpened, { open: openEnterprise, close: closeEnterprise }] = useDisclosure(false);
  const catalogPriceLabels = usePublicCatalogPriceLabels();

  const audienceItems = useMemo(
    () => [
      { icon: IconBuildingHospital, titleKey: "audience.medical.title", bodyKey: "audience.medical.body" },
      { icon: IconBriefcase, titleKey: "audience.practice.title", bodyKey: "audience.practice.body" },
      { icon: IconBarbell, titleKey: "audience.sport.title", bodyKey: "audience.sport.body" },
    ] as const,
    [],
  );

  const featureItems = useMemo(
    () => [
      { icon: IconRobot, titleKey: "features.ai.title", bodyKey: "features.ai.body" },
      { icon: IconLayoutKanban, titleKey: "features.crm.title", bodyKey: "features.crm.body" },
      { icon: IconBuildingBank, titleKey: "features.finance.title", bodyKey: "features.finance.body" },
      { icon: IconDiscount2, titleKey: "features.loyalty.title", bodyKey: "features.loyalty.body" },
      { icon: IconListCheck, titleKey: "features.tasks.title", bodyKey: "features.tasks.body" },
      { icon: IconLayoutDashboard, titleKey: "features.analytics.title", bodyKey: "features.analytics.body" },
    ] as const,
    [],
  );

  const whyItems = useMemo(
    () => [
      { icon: IconBrandMessenger, titleKey: "why.retention.title", bodyKey: "why.retention.body" },
      { icon: IconListCheck, titleKey: "why.routine.title", bodyKey: "why.routine.body" },
      { icon: IconChartLine, titleKey: "why.revenue.title", bodyKey: "why.revenue.body" },
      { icon: IconShieldLock, titleKey: "why.security.title", bodyKey: "why.security.body" },
    ] as const,
    [],
  );

  const landingPlans = useMemo(
    () =>
      MARKETING_PLAN_ORDER.map((slug) => ({
        slug,
        name: tNs("marketing", `plans.${slug}.headline`),
        badge: tNs("marketing", `plans.${slug}.badge`),
        price: catalogPriceLabels[slug],
        period: t("pricing.period"),
        features: [0, 1, 2, 3].map((i) => tNs("marketing", `plans.${slug}.bullets.${i}`)),
        featured: Boolean(PUBLIC_PLAN_MARKETING[slug].featured),
      })),
    [t, i18n.language, catalogPriceLabels],
  );

  const enterpriseBullets = [0, 1, 2].map((i) => tNs("marketing", `enterprise.bullets.${i}`));

  return (
    <Box component="main" className="marketing-landing page-gradient">
      <EnterpriseLeadModal opened={enterpriseOpened} onClose={closeEnterprise} />
      <Box
        component="header"
        py="md"
        px="md"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "rgba(250, 251, 252, 0.82)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(226, 230, 234, 0.9)",
        }}
      >
        <Container size="xl">
          <Group justify="space-between" wrap="wrap" gap="sm">
            <Anchor
              component={Link}
              to={ROUTE_PATHS.marketing.landing}
              fw={800}
              size="lg"
              underline="never"
              style={{ color: "var(--text-main)", letterSpacing: "-0.02em" }}
            >
              {t("brand")}
            </Anchor>
            <Group gap="sm" wrap="wrap" justify="flex-end">
              <Anchor component={Link} to={ROUTE_PATHS.marketing.signup} size="sm" c="dimmed" fw={500}>
                {t("header.plans")}
              </Anchor>
              <Anchor component={Link} to={ROUTE_PATHS.other.login} size="sm" c="dimmed" fw={500}>
                {t("header.patientApp")}
              </Anchor>
              <Button
                component={Link}
                to={ROUTE_PATHS.admin.login}
                variant="subtle"
                color="gray"
                data-testid="landing-staff-sign-in"
              >
                {t("header.signIn")}
              </Button>
              <Button
                component={Link}
                to={ROUTE_PATHS.marketing.signup}
                variant="filled"
                color="slate"
                radius="md"
                rightSection={<ArrowRight size={18} aria-hidden />}
              >
                {t("header.connectOrg")}
              </Button>
              <UiLocaleSwitch />
            </Group>
          </Group>
        </Container>
      </Box>

      <Container size="xl" pt={{ base: 56, md: 80 }} pb={96}>
        <Stack gap={80}>
          <Group align="flex-start" gap={48} wrap="wrap" justify="space-between">
            <Stack gap="xl" maw={640} flex={1} miw={280}>
              <Text size="xs" fw={700} tt="uppercase" c="dimmed" lts={1}>
                {t("hero.kicker")}
              </Text>
              <Title
                order={1}
                style={{
                  fontWeight: 800,
                  letterSpacing: "-0.03em",
                  lineHeight: 1.08,
                  fontSize: "clamp(2rem, 4.2vw, 3.15rem)",
                }}
              >
                {t("hero.title")}
              </Title>
              <Text size="lg" c="dimmed" style={{ lineHeight: 1.65, maxWidth: 560 }}>
                {t("hero.lead")}
              </Text>
              <Group gap="md" mt="sm" wrap="wrap">
                <Button
                  component={Link}
                  to={ROUTE_PATHS.marketing.sandbox}
                  size="xl"
                  radius="md"
                  variant="filled"
                  color="slate"
                >
                  {t("hero.demo")}
                </Button>
                <Button
                  component={Link}
                  to={ROUTE_PATHS.marketing.signup}
                  size="xl"
                  radius="md"
                  variant="outline"
                  color="gray"
                >
                  {t("hero.plans")}
                </Button>
              </Group>
            </Stack>
            <Box flex={1} miw={280} maw={560} w="100%">
              <HeroProductShot alt={t("hero.shotAlt")} />
            </Box>
          </Group>

          <Stack gap="xl" id="audience">
            <Box>
              <Title order={2} style={{ letterSpacing: "-0.02em" }}>
                {t("audience.title")}
              </Title>
              <Text c="dimmed" mt="xs" maw={640}>
                {t("audience.lead")}
              </Text>
            </Box>
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
              {audienceItems.map(({ icon: Icon, titleKey, bodyKey }) => (
                <Paper
                  key={titleKey}
                  className="marketing-bento-card"
                  p="xl"
                  radius="lg"
                  bg="white"
                  style={{ border: "1px solid var(--mantine-color-gray-2)" }}
                >
                  <Stack gap="md">
                    <ThemeIcon variant="light" color="gray" size={48} radius="md">
                      <Icon size={26} stroke={1.5} aria-hidden />
                    </ThemeIcon>
                    <Title order={3} fz="lg">
                      {t(titleKey)}
                    </Title>
                    <Text c="dimmed" size="sm" style={{ lineHeight: 1.65 }}>
                      {t(bodyKey)}
                    </Text>
                  </Stack>
                </Paper>
              ))}
            </SimpleGrid>
          </Stack>

          <Box
            className="marketing-bento-section"
            py={{ base: 48, md: 56 }}
            px={{ base: 20, md: 40 }}
            mx={{ base: -12, sm: 0 }}
          >
            <Stack gap="xl">
              <Box>
                <Title order={2} style={{ letterSpacing: "-0.02em" }}>
                  {t("features.title")}
                </Title>
              </Box>
              <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
                {featureItems.map((item) => {
                  const ModuleIcon = item.icon;
                  return (
                    <Paper
                      key={item.titleKey}
                      className="marketing-bento-card marketing-capability-card"
                      p="xl"
                      radius="lg"
                      bg="white"
                    >
                      <Stack gap="md" justify="space-between" style={{ flex: 1 }}>
                        <ThemeIcon variant="light" color="slate" size={48} radius="md">
                          <ModuleIcon size={26} stroke={1.5} aria-hidden />
                        </ThemeIcon>
                        <Title order={3}>{t(item.titleKey)}</Title>
                        <Text c="dimmed" size="sm" style={{ lineHeight: 1.65, flex: 1 }}>
                          {t(item.bodyKey)}
                        </Text>
                      </Stack>
                    </Paper>
                  );
                })}
              </SimpleGrid>
            </Stack>
          </Box>

          <Stack gap="xl" id="why">
            <Box>
              <Title order={2} style={{ letterSpacing: "-0.02em" }}>
                {t("why.title")}
              </Title>
            </Box>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
              {whyItems.map(({ icon: Icon, titleKey, bodyKey }) => (
                <Group key={titleKey} align="flex-start" wrap="nowrap" gap="md">
                  <ThemeIcon variant="light" color="slate" size={48} radius="md" flex="0 0 auto">
                    <Icon size={26} stroke={1.5} aria-hidden />
                  </ThemeIcon>
                  <Stack gap={6} miw={0}>
                    <Text fw={700} size="md" c="var(--text-main)">
                      {t(titleKey)}
                    </Text>
                    <Text c="dimmed" size="sm" style={{ lineHeight: 1.65 }}>
                      {t(bodyKey)}
                    </Text>
                  </Stack>
                </Group>
              ))}
            </SimpleGrid>
          </Stack>

          <Stack gap="xl" id="pricing">
            <Box>
              <Title order={2} style={{ letterSpacing: "-0.02em" }}>
                {t("pricing.title")}
              </Title>
              <Text c="dimmed" mt="xs" maw={720}>
                {t("pricing.lead")}
              </Text>
            </Box>
            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg" style={{ alignItems: "stretch" }}>
              {landingPlans.map((plan) => (
                <Paper
                  key={plan.slug}
                  className={
                    plan.featured ? "marketing-pricing-card marketing-pricing-card--featured" : "marketing-pricing-card"
                  }
                  p="xl"
                  radius="lg"
                  bg="white"
                  h="100%"
                >
                  <Stack gap="lg" h="100%">
                    <Stack gap={4}>
                      {plan.featured ? (
                        <Text size="xs" fw={700} tt="uppercase" c="teal.7" lts={0.8}>
                          {t("pricing.recommended")}
                        </Text>
                      ) : null}
                      <Title order={3}>{plan.name}</Title>
                      <Text size="sm" c="dimmed" fw={500}>
                        {plan.badge}
                      </Text>
                    </Stack>
                    <Group align="baseline" gap={6} wrap="nowrap">
                      <Text fw={800} fz="xl" style={{ letterSpacing: "-0.02em" }}>
                        {plan.price}
                      </Text>
                      <Text size="sm" c="dimmed" fw={500}>
                        {plan.period}
                      </Text>
                    </Group>
                    <List
                      size="sm"
                      spacing="sm"
                      c="dimmed"
                      icon={
                        <Text component="span" c="slate.6" fw={700}>
                          ·
                        </Text>
                      }
                      styles={{ item: { lineHeight: 1.55 } }}
                    >
                      {plan.features.map((f) => (
                        <List.Item key={f}>{f}</List.Item>
                      ))}
                    </List>
                    <Button
                      component={Link}
                      to={ROUTE_PATHS.marketing.signup}
                      variant={plan.featured ? "filled" : "light"}
                      color={plan.featured ? "slate" : "gray"}
                      fullWidth
                      radius="md"
                      mt="auto"
                    >
                      {t("pricing.choose")}
                    </Button>
                  </Stack>
                </Paper>
              ))}
            </SimpleGrid>

            <Paper
              className="marketing-pricing-card"
              p="xl"
              radius="lg"
              bg="white"
              style={{ border: "1px dashed var(--mantine-color-gray-4)" }}
            >
              <Group justify="space-between" align="flex-start" wrap="wrap" gap="lg">
                <Stack gap="xs" maw={560}>
                  <Title order={3}>{t("enterprise.headline")}</Title>
                  <Text fw={600} c="var(--text-main)">
                    {t("enterprise.priceHint")} · {t("enterprise.priceLabel")}
                  </Text>
                  <List
                    size="sm"
                    spacing="xs"
                    c="dimmed"
                    icon={
                      <Text component="span" c="gray.6" fw={700}>
                        ·
                      </Text>
                    }
                  >
                    {enterpriseBullets.map((line) => (
                      <List.Item key={line}>{line}</List.Item>
                    ))}
                  </List>
                </Stack>
                <Button variant="outline" color="slate" radius="md" onClick={openEnterprise}>
                  {t("pricing.discuss")}
                </Button>
              </Group>
            </Paper>
          </Stack>

          <Stack gap="md" align="center" pt="xl">
            <Button
              component={Link}
              to={ROUTE_PATHS.marketing.signup}
              size="lg"
              radius="md"
              variant="filled"
              color="slate"
              rightSection={<ArrowRight size={18} aria-hidden />}
            >
              {t("header.connectOrg")}
            </Button>
            <Group gap="lg" justify="center" wrap="wrap">
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.signup}>
                {t("footer.catalog")}
              </Anchor>
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.legalPrivacy}>
                {t("footer.privacy")}
              </Anchor>
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.legalTerms}>
                {t("footer.terms")}
              </Anchor>
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.platform.provisionQueue}>
                {t("footer.provision")}
              </Anchor>
            </Group>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
}
