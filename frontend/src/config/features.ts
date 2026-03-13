/** Feature flags. One product, all features enabled. */

export const features = {
  channels_ui: true,
  integrations_1c: true,
  styling: true,
  stickers: true,
  discounts: true,
  feed_stories: true,
  notification_policy_advanced: true,
} as const;

export type Features = typeof features;
