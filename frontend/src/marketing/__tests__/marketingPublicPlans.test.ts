import { describe, expect, it } from "vitest";
import { formatCatalogUsdLabel, LANDING_MONTHLY_PRICE_LABEL, parseCatalogAmount } from "../marketingPublicPlans";

describe("catalog USD labels", () => {
  it("formats integer list prices without cents", () => {
    expect(formatCatalogUsdLabel("20.00")).toBe("$20");
    expect(formatCatalogUsdLabel("100.00")).toBe("$100");
    expect(formatCatalogUsdLabel("200")).toBe("$200");
  });

  it("keeps cents when present", () => {
    expect(formatCatalogUsdLabel("19.50")).toBe("$19.50");
  });

  it("parses catalog decimals", () => {
    expect(parseCatalogAmount("20.00")).toBe(20);
    expect(parseCatalogAmount("1 900,5")).toBe(1900.5);
  });

  it("landing labels match the public ladder", () => {
    expect(LANDING_MONTHLY_PRICE_LABEL.start).toBe("$20");
    expect(LANDING_MONTHLY_PRICE_LABEL.growth).toBe("$100");
    expect(LANDING_MONTHLY_PRICE_LABEL.business_os).toBe("$200");
  });
});
