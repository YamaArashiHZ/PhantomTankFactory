import { describe, it, expect } from "vitest";
import { clampConfig } from "../useAppConfig";
import { DEFAULT_CONFIG, type AppConfig } from "../../types";

describe("clampConfig", () => {
  it("returns defaults when passed null", () => {
    const result = clampConfig(null);
    expect(result).toEqual(DEFAULT_CONFIG);
  });

  it("returns defaults when passed undefined", () => {
    const result = clampConfig(undefined);
    expect(result).toEqual(DEFAULT_CONFIG);
  });

  it("returns defaults for empty object", () => {
    const result = clampConfig({});
    expect(result).toEqual(DEFAULT_CONFIG);
  });

  it("keeps valid values", () => {
    const result = clampConfig({
      brightnessEnhancement: 75,
      brightnessReduction: -25,
      theme: "dark",
      exportDirectory: "/some/path",
      previewQuality: "high",
      previewEnabled: false,
    });
    expect(result.brightnessEnhancement).toBe(75);
    expect(result.brightnessReduction).toBe(-25);
    expect(result.theme).toBe("dark");
    expect(result.exportDirectory).toBe("/some/path");
    expect(result.previewQuality).toBe("high");
    expect(result.previewEnabled).toBe(false);
  });

  it("clamps brightnessEnhancement above 100", () => {
    const result = clampConfig({ brightnessEnhancement: 150 });
    expect(result.brightnessEnhancement).toBe(DEFAULT_CONFIG.brightnessEnhancement);
  });

  it("clamps brightnessEnhancement below 0", () => {
    const result = clampConfig({ brightnessEnhancement: -10 });
    expect(result.brightnessEnhancement).toBe(DEFAULT_CONFIG.brightnessEnhancement);
  });

  it("clamps brightnessReduction below -100", () => {
    const result = clampConfig({ brightnessReduction: -200 });
    expect(result.brightnessReduction).toBe(DEFAULT_CONFIG.brightnessReduction);
  });

  it("clamps brightnessReduction above 0", () => {
    const result = clampConfig({ brightnessReduction: 50 });
    expect(result.brightnessReduction).toBe(DEFAULT_CONFIG.brightnessReduction);
  });

  it("rejects invalid theme", () => {
    const result = clampConfig({ theme: "blue" } as Partial<AppConfig>);
    expect(result.theme).toBe(DEFAULT_CONFIG.theme);
  });

  it("rejects invalid previewQuality", () => {
    const result = clampConfig({ previewQuality: "ultra" } as Partial<AppConfig>);
    expect(result.previewQuality).toBe(DEFAULT_CONFIG.previewQuality);
  });

  it("rejects non-boolean previewEnabled", () => {
    const result = clampConfig({ previewEnabled: "yes" } as unknown as Partial<AppConfig>);
    expect(result.previewEnabled).toBe(DEFAULT_CONFIG.previewEnabled);
  });

  it("rejects non-string exportDirectory", () => {
    const result = clampConfig({ exportDirectory: 123 } as unknown as Partial<AppConfig>);
    expect(result.exportDirectory).toBe("");
  });

  it("fills in missing fields with defaults", () => {
    const result = clampConfig({ theme: "dark" });
    expect(result.theme).toBe("dark");
    expect(result.brightnessEnhancement).toBe(DEFAULT_CONFIG.brightnessEnhancement);
    expect(result.brightnessReduction).toBe(DEFAULT_CONFIG.brightnessReduction);
    expect(result.previewQuality).toBe(DEFAULT_CONFIG.previewQuality);
    expect(result.previewEnabled).toBe(DEFAULT_CONFIG.previewEnabled);
  });
});
