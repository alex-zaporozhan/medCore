import heroFallbackUrl from "@/assets/marketing/landing-admin-workstation.svg?url";
import { EnterpriseLeadModal } from "@/marketing/components/EnterpriseLeadModal";
import { LANDING_HERO_PUBLIC_URLS } from "@/marketing/landingPublicAssets";
import { ENTERPRISE_PLAN_MARKETING, landingPricingCardsForUi } from "@/marketing/marketingPublicPlans";
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
import { useState } from "react";
import { Link } from "react-router-dom";
import "./marketingLanding.css";

function HeroProductShot() {
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
          alt="Интерфейс платформы: навигация, диалоги, CRM и контекст для команды"
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

const audienceItems = [
  {
    icon: IconBuildingHospital,
    title: "Медицина и сфера красоты",
    body: "Стоматологии, клиники, сети салонов. Сложное расписание и учёт материалов.",
  },
  {
    icon: IconBriefcase,
    title: "Частная практика и консалтинг",
    body: "Психологи, юристы, репетиторы. Предоплаты и запись без администратора.",
  },
  {
    icon: IconBarbell,
    title: "Спорт и здоровье",
    body: "Фитнес-студии, йога, массаж. Работа с абонементами и групповыми занятиями.",
  },
];

const featureItems = [
  {
    icon: IconRobot,
    title: "ИИ-ассистент",
    body: "Черновики ответов и маршрутизация диалогов.",
  },
  {
    icon: IconLayoutKanban,
    title: "Управление продажами (CRM)",
    body: "Воронка от первого контакта до оплаты.",
  },
  {
    icon: IconBuildingBank,
    title: "Учёт и финансы",
    body: "Кассы, предоплаты, расчёт зарплат и склад.",
  },
  {
    icon: IconDiscount2,
    title: "Программа лояльности",
    body: "Скидки, абонементы и умные рассылки.",
  },
  {
    icon: IconListCheck,
    title: "Задачи и поручения",
    body: "Контроль сроков и единый рабочий центр.",
  },
  {
    icon: IconLayoutDashboard,
    title: "Аналитика и отчётность",
    body:
      "Панель управления руководителем: от загрузки сотрудников до рентабельности маркетинга в реальном времени без выгрузок в Excel.",
  },
];

const whyItems = [
  {
    icon: IconBrandMessenger,
    title: "Удержание обращений",
    body:
      "Единое окно каналов связи. ИИ отвечает быстро и предлагает свободные слоты, пока администратор занят приёмом.",
  },
  {
    icon: IconListCheck,
    title: "Меньше рутины",
    body:
      "Задачи, расписание и расчёт заработной платы автоматизированы. Нагрузку, которую раньше закрывали несколько сотрудников, можно вести в одном контуре.",
  },
  {
    icon: IconChartLine,
    title: "Выручка с каждого клиента",
    body:
      "Напоминания о визите, списания по абонементу и возврат неактивных клиентов через адресные рассылки.",
  },
  {
    icon: IconShieldLock,
    title: "Безопасность данных",
    body:
      "Разделение данных организаций. ИИ работает с контекстом через слой обезличивания в соответствии с требованиями к персональным данным.",
  },
];

const landingPlans = landingPricingCardsForUi();

export default function MarketingLandingPage() {
  const [enterpriseOpened, { open: openEnterprise, close: closeEnterprise }] = useDisclosure(false);

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
          <Group justify="space-between" wrap="nowrap">
            <Anchor
              component={Link}
              to={ROUTE_PATHS.marketing.landing}
              fw={800}
              size="lg"
              underline="never"
              style={{ color: "var(--text-main)", letterSpacing: "-0.02em" }}
            >
              Единая система управления
            </Anchor>
            <Group gap="sm" wrap="wrap" justify="flex-end">
              <Anchor component={Link} to={ROUTE_PATHS.marketing.signup} size="sm" c="dimmed" fw={500}>
                Тарифы
              </Anchor>
              <Anchor component={Link} to={ROUTE_PATHS.other.login} size="sm" c="dimmed" fw={500}>
                Приложение пациента
              </Anchor>
              <Button component={Link} to={ROUTE_PATHS.other.login} variant="subtle" color="gray">
                Войти
              </Button>
              <Button
                component={Link}
                to={ROUTE_PATHS.marketing.signup}
                variant="filled"
                color="slate"
                radius="md"
                rightSection={<ArrowRight size={18} aria-hidden />}
              >
                Подключить организацию
              </Button>
            </Group>
          </Group>
        </Container>
      </Box>

      <Container size="xl" pt={{ base: 56, md: 80 }} pb={96}>
        <Stack gap={80}>
          <Group align="flex-start" gap={48} wrap="wrap" justify="space-between">
            <Stack gap="xl" maw={640} flex={1} miw={280}>
              <Text size="xs" fw={700} tt="uppercase" c="dimmed" lts={1}>
                Единая система управления · Облачное решение для бизнеса
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
                Операционная система для роста вашего бизнеса
              </Title>
              <Text size="lg" c="dimmed" style={{ lineHeight: 1.65, maxWidth: 560 }}>
                ИИ-коммуникации, расписание, CRM и учёт в одном окне. Освободите команду от рутины и увеличьте
                выручку.
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
                  Смотреть демо
                </Button>
                <Button
                  component={Link}
                  to={ROUTE_PATHS.marketing.signup}
                  size="xl"
                  radius="md"
                  variant="outline"
                  color="gray"
                >
                  Тарифы
                </Button>
              </Group>
            </Stack>
            <Box flex={1} miw={280} maw={560} w="100%">
              <HeroProductShot />
            </Box>
          </Group>

          <Stack gap="xl" id="audience">
            <Box>
              <Title order={2} style={{ letterSpacing: "-0.02em" }}>
                Для кого это работает
              </Title>
              <Text c="dimmed" mt="xs" maw={640}>
                Разработано для компаний, где важна плотная запись, контроль финансов и возвратность клиентов.
              </Text>
            </Box>
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
              {audienceItems.map(({ icon: Icon, title, body }) => (
                <Paper
                  key={title}
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
                      {title}
                    </Title>
                    <Text c="dimmed" size="sm" style={{ lineHeight: 1.65 }}>
                      {body}
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
                  Возможности
                </Title>
              </Box>
              <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
                {featureItems.map((item) => {
                  const ModuleIcon = item.icon;
                  return (
                    <Paper
                      key={item.title}
                      className="marketing-bento-card marketing-capability-card"
                      p="xl"
                      radius="lg"
                      bg="white"
                    >
                      <Stack gap="md" justify="space-between" style={{ flex: 1 }}>
                        <ThemeIcon variant="light" color="slate" size={48} radius="md">
                          <ModuleIcon size={26} stroke={1.5} aria-hidden />
                        </ThemeIcon>
                        <Title order={3}>{item.title}</Title>
                        <Text c="dimmed" size="sm" style={{ lineHeight: 1.65, flex: 1 }}>
                          {item.body}
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
                Преимущества платформы
              </Title>
            </Box>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
              {whyItems.map(({ icon: Icon, title, body }) => (
                <Group key={title} align="flex-start" wrap="nowrap" gap="md">
                  <ThemeIcon variant="light" color="slate" size={48} radius="md" flex="0 0 auto">
                    <Icon size={26} stroke={1.5} aria-hidden />
                  </ThemeIcon>
                  <Stack gap={6} miw={0}>
                    <Text fw={700} size="md" c="var(--text-main)">
                      {title}
                    </Text>
                    <Text c="dimmed" size="sm" style={{ lineHeight: 1.65 }}>
                      {body}
                    </Text>
                  </Stack>
                </Group>
              ))}
            </SimpleGrid>
          </Stack>

          <Stack gap="xl" id="pricing">
            <Box>
              <Title order={2} style={{ letterSpacing: "-0.02em" }}>
                Тарифы
              </Title>
              <Text c="dimmed" mt="xs" maw={720}>
                Выберите решение под масштаб вашего бизнеса.
              </Text>
            </Box>
            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
              {landingPlans.map((plan) => (
                <Paper
                  key={plan.slug}
                  className={
                    plan.featured ? "marketing-pricing-card marketing-pricing-card--featured" : "marketing-pricing-card"
                  }
                  p="xl"
                  radius="lg"
                  bg="white"
                >
                  <Stack gap="lg" h="100%">
                    <Stack gap={4}>
                      {plan.featured ? (
                        <Text size="xs" fw={700} tt="uppercase" c="teal.7" lts={0.8}>
                          Рекомендуем
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
                      Выбрать
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
                  <Title order={3}>{ENTERPRISE_PLAN_MARKETING.headline}</Title>
                  <Text fw={600} c="var(--text-main)">
                    {ENTERPRISE_PLAN_MARKETING.priceHint} · {ENTERPRISE_PLAN_MARKETING.priceLabel}
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
                    {ENTERPRISE_PLAN_MARKETING.bullets.map((line) => (
                      <List.Item key={line}>{line}</List.Item>
                    ))}
                  </List>
                </Stack>
                <Button variant="outline" color="slate" radius="md" onClick={openEnterprise}>
                  Обсудить внедрение
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
              Подключить организацию
            </Button>
            <Group gap="lg" justify="center" wrap="wrap">
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.signup}>
                Каталог на сайте
              </Anchor>
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.legalPrivacy}>
                Конфиденциальность
              </Anchor>
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.marketing.legalTerms}>
                Условия использования
              </Anchor>
              <Anchor component={Link} size="sm" c="dimmed" to={ROUTE_PATHS.platform.provisionQueue}>
                Очередь внедрения
              </Anchor>
            </Group>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
}
