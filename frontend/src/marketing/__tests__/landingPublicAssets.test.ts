import { describe, expect, it } from "vitest";
import { publicUrlFromRoot } from "../landingPublicAssets";

describe("landingPublicAssets", () => {
  it("joins base with trailing slash and path without leading slash", () => {
    expect(publicUrlFromRoot("marketing/x.webp", "/app/")).toBe("/app/marketing/x.webp");
  });

  it("adds slash when base has no trailing slash", () => {
    expect(publicUrlFromRoot("marketing/x.png", "/app")).toBe("/app/marketing/x.png");
  });

  it("strips leading slashes from path", () => {
    expect(publicUrlFromRoot("/marketing/x.jpg", "/")).toBe("/marketing/x.jpg");
  });
});
