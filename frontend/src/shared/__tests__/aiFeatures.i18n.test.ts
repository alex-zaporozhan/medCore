import { afterEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { getAiFeatureTooltip, getDefaultAiFeatures } from "../aiFeatures";

describe("aiFeatures i18n", () => {
  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("returns EN tooltip and labels by default", () => {
    expect(getAiFeatureTooltip("stub")).toBe(
      "Stub/demo: the feature is in development. Real backend/tool calls are disabled.",
    );
    const spotlight = getDefaultAiFeatures().find((f) => f.id === "omni.spotlight.agent");
    expect(spotlight?.label).toBe("Spotlight AI agent");
    expect(spotlight?.label).not.toMatch(/[А-Яа-яЁё]/);
    expect(i18n.t("ai.toolsUnavailable")).toBe(
      "Not enough permissions, or the backend tool is unavailable.",
    );
  });

  it("returns RU tooltip after changeLanguage", async () => {
    await i18n.changeLanguage("ru");
    expect(getAiFeatureTooltip("stub")).toBe(
      "Stub/демо: функция в разработке. Реальные вызовы backend/tools отключены.",
    );
  });
});
