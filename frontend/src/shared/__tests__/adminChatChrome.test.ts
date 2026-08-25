import { describe, expect, it } from "vitest";

import {
  adminChatOmniClientInboundBubbleStyle,
  adminChatOmniOutboundBubbleStyle,
  adminChatOutgoingBubbleStyle,
} from "../adminChatChrome";

describe("adminChatOmni bubble styles", () => {
  it("outgoing omni bubble matches staff outgoing token", () => {
    expect(adminChatOmniOutboundBubbleStyle()).toEqual(adminChatOutgoingBubbleStyle());
  });

  it("incoming omni bubble uses surface and hairline", () => {
    const inbound = adminChatOmniClientInboundBubbleStyle();
    expect(inbound.backgroundColor).toBe("var(--bg-card)");
    expect(inbound.border).toBe("1px solid var(--mantine-color-gray-2)");
    expect(inbound).not.toHaveProperty("boxShadow");
  });
});
