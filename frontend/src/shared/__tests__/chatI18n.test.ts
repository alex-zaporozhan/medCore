import { describe, expect, it } from "vitest";

import {
  isOmniChannelCreatableType,
  omniChannelCreateTypeOptions,
  omniChannelTypeLabel,
} from "../chatI18n";

describe("chatI18n omni channels", () => {
  it("excludes VK_BOT from create options", () => {
    expect(omniChannelCreateTypeOptions().some((o) => o.value === "VK_BOT")).toBe(false);
    expect(isOmniChannelCreatableType("VK_BOT")).toBe(false);
    expect(isOmniChannelCreatableType("TELEGRAM_BOT")).toBe(true);
  });

  it("keeps legacy VK label for existing rows", () => {
    expect(omniChannelTypeLabel("VK_BOT")).toMatch(/VK/i);
  });
});
