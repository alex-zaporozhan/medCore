import { usePublicFeed, usePublicStories } from "@/hooks/usePublicFeed";
import { useClinics } from "@/hooks";
import {
  Anchor,
  Card,
  Group,
  Loader,
  ScrollArea,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { QueryErrorAlert } from "@/shared/ui";
import { SEMANTIC } from "@/shared/semanticUi";

export default function FeedPage() {
  const { data: clinics } = useClinics();
  const clinicId = clinics?.[0]?.id ?? null;
  const { data: feed, isLoading: feedLoading, isError: feedError, error: feedErr } = usePublicFeed(clinicId);
  const { data: stories, isLoading: storiesLoading } = usePublicStories(clinicId);

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>Лента</Title>
        <Text size="sm" c="dimmed">Нет выбранной клиники.</Text>
      </Stack>
    );
  }

  const posts = feed ?? [];
  const storyList = stories ?? [];

  return (
    <Stack gap="lg">
      <Title order={3}>Лента</Title>
      <Text size="sm" c="dimmed">
        Акции, новости и спецпредложения клиники. Сторис — короткие предложения, посты — подробные акции и новости.
      </Text>

      {storyList.length > 0 && (
        <Stack gap="xs">
          <Text size="sm" fw={500} c="dimmed">Сторис</Text>
          <ScrollArea type="scroll" scrollbarSize="xs">
            <Group gap="md" wrap="nowrap" align="stretch">
              {storyList.map((s) => (
                <Card
                  key={s.id}
                  shadow="sm"
                  radius="md"
                  withBorder
                  p={0}
                  w={120}
                  style={{ overflow: "hidden", flexShrink: 0 }}
                >
                  {s.media_type === "video" && s.media_url ? (
                    <video
                      src={s.media_url}
                      controls
                      style={{
                        width: "100%",
                        aspectRatio: "9/16",
                        minHeight: 160,
                        objectFit: "cover",
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        aspectRatio: "9/16",
                        background: s.media_url
                          ? `center/cover url(${s.media_url})`
                          : "var(--bg-card-soft)",
                        minHeight: 160,
                      }}
                    />
                  )}
                  {s.caption && (
                    <Text size="xs" p="xs" lineClamp={2}>
                      {s.caption}
                    </Text>
                  )}
                </Card>
              ))}
            </Group>
          </ScrollArea>
        </Stack>
      )}

      <Stack gap="xs">
        <Text size="sm" fw={500} c="dimmed">Акции и новости</Text>
        {storiesLoading || feedLoading ? (
          <Loader size="sm" />
        ) : feedError ? (
          <QueryErrorAlert error={feedErr} title="Не удалось загрузить ленту" />
        ) : posts.length === 0 ? (
          <Text size="sm" c="dimmed">Пока нет записей в ленте.</Text>
        ) : (
          <Stack gap="lg" maw={760} mx="auto" w="100%">
            {posts.map((p) => (
              <Card
                key={p.id}
                shadow="sm"
                radius="lg"
                withBorder
                p="lg"
                style={{ width: "100%" }}
              >
                <Stack gap="xs">
                  <Title order={4}>{p.title}</Title>
                  {p.video_url && (
                    <video
                      src={p.video_url}
                      controls
                      style={{
                        width: "100%",
                        maxWidth: "100%",
                        aspectRatio: "16/9",
                        objectFit: "cover",
                        borderRadius: "var(--radius-md)",
                      }}
                    />
                  )}
                  {p.image_url && !p.video_url && (
                    <img
                      src={p.image_url}
                      alt=""
                      style={{
                        width: "100%",
                        maxWidth: "100%",
                        aspectRatio: "16/9",
                        objectFit: "cover",
                        borderRadius: "var(--radius-md)",
                      }}
                    />
                  )}
                  {p.additional_image_urls && p.additional_image_urls.length > 0 && (
                    <Group gap="xs" wrap="wrap">
                      {p.additional_image_urls.map((url: string, i: number) => (
                        <img
                          key={i}
                          src={url}
                          alt=""
                          style={{
                            width: 110,
                            aspectRatio: "4/3",
                            objectFit: "cover",
                            borderRadius: "var(--radius-md)",
                          }}
                        />
                      ))}
                    </Group>
                  )}
                  {p.image_url && p.video_url && (
                    <img
                      src={p.image_url}
                      alt=""
                      style={{
                        width: "100%",
                        maxWidth: "100%",
                        aspectRatio: "16/9",
                        objectFit: "cover",
                        borderRadius: "var(--radius-md)",
                      }}
                    />
                  )}
                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                    {p.body}
                  </Text>
                  {p.link && (
                    <Anchor
                      href={p.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="sm"
                      c={SEMANTIC.action.link}
                      fw={500}
                    >
                      Подробнее
                    </Anchor>
                  )}
                </Stack>
              </Card>
            ))}
          </Stack>
        )}
      </Stack>

      <Anchor component={Link} to={ROUTE_PATHS.patient.booking} size="sm" c={SEMANTIC.action.confirm} fw={500}>
        Записаться на приём
      </Anchor>
    </Stack>
  );
}
