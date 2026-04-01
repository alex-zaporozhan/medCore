@QA_ARCH я решил сделать полностью передел нашего дизайна. 

Я хочу чтобы ты ориентировался на следующие решение и сделал единый техпаспорт и поменял бы всё в дизайне по эти решения, как и архитектурные файлы. 

Замечание: это подсказка от Gemini которая не проиндексирована с нашим проектом, потому твои решения в спорных ситуациях будут в приоритете, ты архитектор и дизайнер и руководишь проектом. Это просто новые ТЗ чтобы освежить наш фронт.

Можешь создать себе подробную инструкцию по внедрению перемен чтобы было чисто E2E.

Поскольку это универсальное бизнес-решение (SaaS), нам нужен стиль «Инструмент», а не «Сайт». Интерфейс должен уйти на второй план, пропуская данные вперед.
Ниже представлен полный техпаспорт (Design System Foundation) для вашего стека Mantine + Vite + React.
1. Типографика (The Foundation)
Для бизнес-интерфейса критична читаемость цифр в таблицах.
Основной шрифт: Inter (Google Fonts — бесплатно).
Альтернатива: Geist (Open Source — бесплатно).
Настройка: Используйте tabular-nums для цифр, чтобы колонки в таблицах и расписании не «прыгали».


1. Подключение шрифта (Index.html или CSS)
Добавьте этот импорт в начало вашего глобального index.css:
css
@import url('https://fonts.googleapis.com');

:root {
  /* Важнейшая настройка для ERP: табличные цифры и улучшенная читаемость */
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-feature-settings: "cv02", "cv05", "cv11", "tnum"; 
  -webkit-font-smoothing: antialiased;
}
Используйте код с осторожностью.

tnum (tabular numbers) сделает все цифры одинаковой ширины — это критично для расписания и цен в CRM.
2. Финальный конфиг темы (App.tsx)
Здесь мы связываем шрифт с компонентами Mantine:
tsx
import { MantineProvider, createTheme, rem } from '@mantine/core';

const theme = createTheme({
  primaryColor: 'dark',
  // Указываем Inter как основной шрифт для всей системы
  fontFamily: 'Inter, sans-serif',
  headings: {
    fontFamily: 'Inter, sans-serif',
    fontWeight: '700',
  },

  // Настройка плотности (Density) для взрослого SaaS
  spacing: {
    xs: rem(8),
    sm: rem(12),
    md: rem(16),
    lg: rem(24),
    xl: rem(32),
  },

  components: {
    Text: {
      defaultProps: {
        size: 'sm', // 14px — стандарт для серьезного софта
      },
    },
    // Все остальные настройки Midnight (dark, ai, success), 
    // которые мы обсуждали ранее...
  },
});

export default function App() {
  return (
    <MantineProvider theme={theme}>
      {/* Ваш Layout здесь */}
    </MantineProvider>
  );
}


2. Цветовой паспорт (Midnight & Graphite)
В этой схеме мы используем Slate (синевато-серый) для интерфейса, так как чистый черный на белом слишком контрастен и утомляет глаза.
Основная палитра (Grays)
Токен	HEX	Применение
Surface Low	#F8FAFC	Общий фон страницы (не белый!)
Surface High	#FFFFFF	Карточки, модальные окна, контент
Border Soft	#E2E8F0	Разделители, границы карточек
Text Main	#0F172A	Заголовки, основной текст
Text Muted	#64748B	Подписи, плейсхолдеры, иконки
Функциональные акценты (Semantic)
Смысл	Цвет	Применение
Action	#1E293B	Основные кнопки (темный графит)
AI (RAG)	#7C3AED	Фиолетовый (интеллект, поиск, подсказки)
Success	#10B981	Подтвержденные записи, оплата, "Ок"
Danger	#EF4444	Отмены, долги, ошибки
Warning	#F59E0B	Задачи в работе, напоминания
3. Реализация в Mantine (Theme Object)
Скопируйте это в ваш файл конфигурации темы. Это создаст «взрослый» вид системы по умолчанию для всех компонентов.
tsx
import { createTheme, rem } from '@mantine/core';

export const businessTheme = createTheme({
  primaryColor: 'dark',
  fontFamily: 'Inter, sans-serif',
  
  // Настройка размеров для плотного ERP-интерфейса
  fontSizes: {
    xs: rem(12),
    sm: rem(14), // Основной размер текста
    md: rem(16),
  },

  colors: {
    // Насыщенный Slate для Midnight стиля
    dark: [
      '#f8fafc', '#f1f5f9', '#e2e8f0', '#cbd5e1', '#94a3b8', 
      '#64748b', '#475569', '#334155', '#1e293b', '#0f172a'
    ],
    // Специальный бренд-цвет для AI функций
    ai: ['#f5f3ff', '#ede9fe', '#ddd6fe', '#c4b5fd', '#a78bfa', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6', '#4c1d95'],
  },

  components: {
    // Карточки в стиле бизнес-премиум
    Paper: {
      defaultProps: {
        withBorder: true,
        shadow: 'none', // В бизнесе тени — это шум, используем границы
        p: 'md',
        radius: 'sm',
      },
    },
    // Кнопки: строгие, без градиентов
    Button: {
      defaultProps: {
        radius: 'sm',
        fw: 600,
      },
      styles: {
        root: { transition: 'background-color 0.2s ease' }
      }
    },
    // Инпуты делаем максимально чистыми
    Input: {
      styles: (theme) => ({
        input: {
          backgroundColor: 'transparent',
          '&:focus': { borderColor: theme.colors.dark[8] }
        }
      })
    },
    // Таблицы — сердце ERP
    Table: {
      defaultProps: {
        verticalSpacing: 'sm',
        horizontalSpacing: 'md',
        withRowBorders: true,
        highlightOnHover: true,
      },
      styles: {
        thead: { backgroundColor: '#f8fafc' }, // Легкий фон у шапки
      }
    }
  }
});
Используйте код с осторожностью.

4. Визуальные приемы для вашего интерфейса
Sidebar (Навигация): Сделайте его white (белым) с тонкой серой границей справа (border-right: 1px solid #E2E8F0). Активный пункт меню выделяйте не синим фоном, а черным жирным текстом и тонкой вертикальной черной линией слева (высотой 20px). Это стиль Stripe/Linear.
AI Блок: На вашем скрине чат — это основное действие. Используйте для него Paper с фоном var(--mantine-color-ai-0) (почти белый фиолетовый) и иконку IconSparkles.
Бейджи (Badges): Вместо залитых цветом плашек используйте variant="dot". Например, для статуса "Клиент" — просто серая точка, для "Запись" — зеленая. Это разгрузит экран.
Разделение: Используйте Divider с очень низкой прозрачностью. Линии должны быть едва заметны — их задача направлять глаз, а не резать экран.

Этот сайдбар спроектирован по канонам «High-Density ERP» (высокая плотность данных). Мы уходим от громоздких синих плашек к тонким линиям, качественной типографике и акцентам в стиле Linear/Stripe.
Подготовка: Установка шрифта
Для этого стиля критически важен шрифт Inter. Добавьте его в свой проект (например, через index.html или импорт в CSS):
html
<link href="https://fonts.googleapis.com" rel="stylesheet">
Используйте код с осторожностью.

Код компонента Sidebar (React + Mantine)
Этот компонент использует AppShell от Mantine. Он разделен на логические блоки: «Операции», «Бизнес» и т.д., как на вашем скриншоте, но с более чистой иерархией.
tsx
import { useState } from 'react';
import { 
  Box, 
  NavLink, 
  Text, 
  Stack, 
  Group, 
  ThemeIcon, 
  Divider, 
  ScrollArea,
  rem 
} from '@mantine/core';
import { 
  IconLayoutDashboard, 
  IconCalendarEvent, 
  IconMessageChatbot, 
  IconUsers, 
  IconCreditCard, 
  IconStar,
  IconChecklist,
  IconChartBar,
  IconArrowLeft
} from '@tabler/icons-react';

const data = [
  { group: 'OPERATIONS', items: [
    { label: 'Dashboard', icon: IconLayoutDashboard },
    { label: 'Schedule & Bookings', icon: IconCalendarEvent },
    { label: 'Chat & AI', icon: IconMessageChatbot, active: true },
  ]},
  { group: 'BUSINESS', items: [
    { label: 'CRM & Sales', icon: IconUsers },
    { label: 'Finance', icon: IconCreditCard },
    { label: 'Loyalty', icon: IconStar },
    { label: 'Tasks', icon: IconChecklist },
    { label: 'Analytics / Reports', icon: IconChartBar },
  ]},
];

export function MidnightSidebar() {
  const [active, setActive] = useState('Chat & AI');

  return (
    <Box 
      component="nav" 
      style={{ 
        height: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        borderRight: `${rem(1)} solid var(--mantine-color-dark-2)`,
        backgroundColor: 'var(--mantine-color-white)'
      }}
    >
      {/* Логотип / Название клиники */}
      <Group p="md" justify="space-between">
        <Text fw={700} size="sm" c="dark.9" style={{ letterSpacing: rem(-0.5) }}>
          ДЕМО СТОМАТОЛОГИЯ
        </Text>
      </Group>

      <ScrollArea flex={1} px="sm">
        {data.map((section) => (
          <Box key={section.group} mb="xl">
            <Text 
              size="xs" 
              fw={700} 
              c="dark.3" 
              mb="xs" 
              pl="sm" 
              style={{ letterSpacing: rem(1) }}
            >
              {section.group}
            </Text>
            
            <Stack gap={4}>
              {section.items.map((item) => (
                <NavLink
                  key={item.label}
                  active={item.label === active}
                  label={item.label}
                  leftSection={<item.icon size={18} stroke={1.5} />}
                  onClick={() => setActive(item.label)}
                  variant="subtle"
                  styles={(theme) => ({
                    root: {
                      borderRadius: theme.radius.sm,
                      padding: `${rem(8)} ${rem(12)}`,
                      color: theme.colors.dark[5],
                      backgroundColor: 'transparent',
                      '&[data-active]': {
                        backgroundColor: 'transparent',
                        color: theme.colors.dark[9],
                        fontWeight: 600,
                        position: 'relative',
                        // Та самая "дорогая" черная полоска слева
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          left: rem(-10),
                          top: rem(8),
                          bottom: rem(8),
                          width: rem(3),
                          backgroundColor: theme.colors.dark[9],
                          borderRadius: `0 ${rem(4)} ${rem(4)} 0`,
                        }
                      },
                      '&:hover': {
                        backgroundColor: theme.colors.dark[0],
                      }
                    },
                    label: { fontSize: theme.fontSizes.sm }
                  })}
                />
              ))}
            </Stack>
          </Box>
        ))}
      </ScrollArea>

      {/* Футер сайдбара */}
      <Box p="md" style={{ borderTop: `${rem(1)} solid var(--mantine-color-dark-2)` }}>
        <NavLink
          label="Выйти"
          leftSection={<IconArrowLeft size={18} stroke={1.5} />}
          c="dark.3"
        />
      </Box>
    </Box>
  );
}
Используйте код с осторожностью.

Почему это работает лучше:
Контраст и акценты: Вместо того чтобы заливать весь активный пункт синим цветом, мы используем черную вертикальную линию слева. Это визуальный код профессионального софта (как в Slack или Linear).
Типографика: Межбуквенное расстояние (letter-spacing) у заголовков групп (OPERATIONS) увеличено, что придает им вид «метки», а не просто текста.
Иерархия: Мы используем цвет dark.3 (мягкий серый) для иконок и названий, которые не активны. Это «гасит» второстепенные элементы, фокусируя внимание на текущем разделе.
Сетка: Мы добавили ScrollArea, чтобы при большом количестве пунктов меню (что часто бывает в ERP) интерфейс оставался стабильным.
Как интегрировать:
Просто поместите MidnightSidebar внутрь пропса navbar компонента AppShell от Mantine.

Для реализации «умного» чата в стиле Midnight & Graphite мы отойдем от привычных «бабблов» мессенджеров. В бизнес-интерфейсе чат — это поток данных. Мы выделим ответы AI через фиолетовый акцент и структуру «карточки-инсайта».
Концепция интерфейса чата:
Сообщения пациента: Максимально простые, на белом фоне с тонкой серой рамкой.
Ответы AI (RAG): Фиолетовая индикация слева, легкий фиолетовый фон и четкие блоки: «Инсайт», «Источник» (ссылка на базу знаний) и «Рекомендация».
Интерактив: Кнопки действий прямо внутри карточки AI (например, «Записать на прием»).
Код компонента чата (Mantine + React)
tsx
import { 
  Paper, 
  Text, 
  Group, 
  Stack, 
  Avatar, 
  Badge, 
  ThemeIcon, 
  ActionIcon,
  Button,
  Box,
  rem
} from '@mantine/core';
import { IconSparkles, IconExternalLink, IconCornerUpRightDouble, IconDots } from '@tabler/icons-react';

// Компонент сообщения от AI
export function AIChatInsight({ content, sources, suggestion }) {
  return (
    <Paper 
      shadow="none" 
      p="md" 
      mb="lg"
      bg="var(--mantine-color-ai-0)" // Очень светлый фиолетовый
      style={{ 
        border: `${rem(1)} solid var(--mantine-color-ai-2)`,
        borderLeft: `${rem(4)} solid var(--mantine-color-ai-filled)`,
        position: 'relative'
      }}
    >
      {/* Шапка карточки AI */}
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <ThemeIcon color="ai" variant="filled" size="sm" radius="xl">
            <IconSparkles size={14} />
          </ThemeIcon>
          <Text size="xs" fw={700} c="ai.9" tt="uppercase" lts={rem(0.5)}>
            AI Ассистент (RAG)
          </Text>
        </Group>
        <Badge variant="outline" color="ai" size="xs">Анализ записи</Badge>
      </Group>

      {/* Основной текст ответа */}
      <Text size="sm" c="dark.8" lh={1.6} mb="md">
        {content}
      </Text>

      {/* Блок источников (RAG специфика) */}
      {sources && (
        <Box 
          p="xs" 
          bg="white" 
          style={{ borderRadius: rem(4), border: `${rem(1)} dashed var(--mantine-color-ai-3)` }}
          mb="md"
        >
          <Text size="xs" fw={600} c="dark.3" mb={4}>ИСТОЧНИКИ:</Text>
          <Group gap={8}>
            {sources.map((src, i) => (
              <Badge 
                key={i} 
                variant="light" 
                color="gray" 
                size="xs" 
                rightSection={<IconExternalLink size={10} />}
                component="a"
                href="#"
                style={{ cursor: 'pointer' }}
              >
                {src}
              </Badge>
            ))}
          </Group>
        </Box>
      )}

      {/* Быстрое действие */}
      <Group justify="flex-end">
        <Button 
          variant="light" 
          color="ai" 
          size="xs" 
          leftSection={<IconCornerUpRightDouble size={14} />}
        >
          {suggestion || 'Применить рекомендацию'}
        </Button>
      </Group>
    </Paper>
  );
}

// Пример сообщения от пациента (Классика Midnight)
export function PatientMessage({ name, message, time }) {
  return (
    <Group align="flex-start" mb="lg" wrap="nowrap">
      <Avatar color="dark" radius="sm" size="sm">{name[0]}</Avatar>
      <Stack gap={4} flex={1}>
        <Group justify="space-between">
          <Text size="xs" fw={700} c="dark.9">{name}</Text>
          <Text size="xs" c="dark.3">{time}</Text>
        </Group>
        <Paper withBorder p="sm" bg="white">
          <Text size="sm" c="dark.7" lh={1.5}>{message}</Text>
        </Paper>
      </Stack>
      <ActionIcon variant="subtle" color="gray" size="sm">
        <IconDots size={16} />
      </ActionIcon>
    </Group>
  );
}
Используйте код с осторожностью.

Ключевые UX-фишки для вашего SaaS:
Прозрачность AI: Мы добавили блок «Источники». В серьезных системах (особенно медицине) пользователю важно знать, почему AI так решил. Это повышает доверие.
Визуальный шум: Мы убрали синий фон у сообщений пациента. Теперь весь интерфейс монохромный, а единственное яркое пятно — это AI. Это мгновенно фокусирует взгляд оператора на самой важной интеллектуальной части.
Кнопки действий: Вместо того чтобы врач искал, где записать пациента после чата, мы предлагаем контекстное действие прямо в карточке AI.
Геометрия: Использование radius="sm" (4px) вместо стандартных круглых бабблов делает интерфейс более архитектурным и профессиональным.

В стиле Midnight & Graphite верхняя панель (Header) должна работать как навигатор: четкое разделение потоков данных и мгновенный доступ к фильтрам. Мы уберем «синие кнопки» из вашего скриншота и заменим их на Segmented Control или Tabs с тонкими акцентами.
Главная фишка здесь — индикаторы плотности. Мы покажем количество сообщений прямо в фильтрах, не перегружая интерфейс.
Код Header с фильтрами (Mantine + React)
tsx
import { 
  Group, 
  Text, 
  Tabs, 
  Badge, 
  TextInput, 
  ActionIcon, 
  Menu, 
  Divider,
  rem 
} from '@mantine/core';
import { 
  IconSearch, 
  IconFilter, 
  IconChevronDown, 
  IconCircleFilled 
} from '@tabler/icons-react';

export function ChatHeader() {
  return (
    <Group 
      h={60} 
      px="md" 
      justify="space-between" 
      style={{ borderBottom: `${rem(1)} solid var(--mantine-color-dark-2)` }}
    >
      {/* Левая часть: Заголовок и быстрый поиск */}
      <Group gap="xl">
        <Text fw={700} size="lg" c="dark.9">Чаты</Text>
        
        <TextInput
          placeholder="Поиск по контакту..."
          size="xs"
          leftSection={<IconSearch size={14} stroke={1.5} />}
          styles={{
            input: {
              width: rem(240),
              backgroundColor: 'var(--mantine-color-dark-0)',
              border: 'none',
              '&:focus': { backgroundColor: 'white', border: `${rem(1)} solid var(--mantine-color-dark-2)` }
            }
          }}
        />
      </Group>

      {/* Центр: Фильтры статусов (Вместо синих кнопок) */}
      <Tabs variant="pills" defaultValue="all" styles={(theme) => ({
        root: { backgroundColor: theme.colors.dark[0], padding: rem(2), borderRadius: theme.radius.sm },
        tab: {
          fontSize: theme.fontSizes.xs,
          fontWeight: 600,
          padding: `${rem(4)} ${rem(12)}`,
          '&[data-active]': {
            backgroundColor: 'white',
            color: theme.colors.dark[9],
            boxShadow: theme.shadows.xs,
          },
        },
      })}>
        <Tabs.List>
          <Tabs.Tab value="all">
            Все <Badge variant="transparent" size="xs" c="dark.3" ml={4}>42</Badge>
          </Tabs.Tab>
          <Tabs.Tab value="unread">
            Неотвеченные <Badge color="danger" variant="filled" size="xs" ml={4}>5</Badge>
          </Tabs.Tab>
          <Tabs.Tab value="ai">
            AI Требует внимания <IconCircleFilled size={6} color="var(--mantine-color-ai-6)" style={{marginLeft: 6}} />
          </Tabs.Tab>
          <Tabs.Tab value="vip">VIP</Tabs.Tab>
        </Tabs.List>
      </Tabs>

      {/* Правая часть: Доп. фильтры и настройки вида */}
      <Group gap="xs">
        <Menu shadow="md" width={200} position="bottom-end">
          <Menu.Target>
            <ActionIcon variant="default" size="lg" radius="sm">
              <IconFilter size={18} stroke={1.5} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Label>Сортировка</Menu.Label>
            <Menu.Item>Сначала новые</Menu.Item>
            <Menu.Item>По приоритету</Menu.Item>
            <Divider />
            <Menu.Label>Статус диалога</Menu.Label>
            <Menu.Item color="success.6">Завершенные</Menu.Item>
          </Menu.Dropdown>
        </Menu>

        <Divider orientation="vertical" h={20} my="auto" />

        <Group gap={4} style={{ cursor: 'pointer' }}>
          <Text size="xs" fw={600} c="dark.9">Все режимы</Text>
          <IconChevronDown size={14} />
        </Group>
      </Group>
    </Group>
  );
}
Используйте код с осторожностью.

Почему этот Header «взрослее» того, что на скрине:
Tabs вместо Buttons: Кнопки «Все», «Неотвеченные» и т.д. на скриншоте спорят за внимание. Использование Tabs (Pills) на светло-серой подложке создает единую визуальную область, которая интуитивно понятна как переключатель режимов.
Умные бейджи: Вкладка «Неотвеченные» сразу подсвечивает проблему красным цветом, а вкладка с AI — фиолетовым. Это цветовое кодирование без излишеств.
Поиск в шапке: Перенос поиска в Header освобождает место в боковой панели или основном контенте, делая рабочую область чище.
Разделение действий: Основные фильтры — на виду, второстепенные (сортировка, настройки) — спрятаны в Menu. Это золотое правило ERP: «Progressive Disclosure» (раскрытие информации по мере необходимости).
Резюме стиля Midnight для вашего SaaS:
Теперь у вас есть:
Sidebar: Белый, строгий, с черным акцентом.
Header: Функциональный, с мягкой группировкой фильтров.
Content (AI): Интеллектуальные карточки с фиолетовым фокусом.
Этот набор превращает «просто чат» в мощный бизнес-инструмент.