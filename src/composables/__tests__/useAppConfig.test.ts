import { describe, it, expect } from "vitest";
import { clampConfig } from "../useAppConfig";
import { DEFAULT_CONFIG, DEFAULT_MODE_PARAMS, type AppConfig } from "../../types";

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
      theme: "dark",
      exportDirectory: "/some/path",
      previewQuality: "high",
      previewEnabled: false,
      colorMode: "color",
    } as Partial<AppConfig>);
    expect(result.theme).toBe("dark");
    expect(result.exportDirectory).toBe("/some/path");
    expect(result.previewQuality).toBe("high");
    expect(result.previewEnabled).toBe(false);
    expect(result.colorMode).toBe("color");
  });

  it("clamps grayscale brightnessEnhancement above 100", () => {
    const result = clampConfig({
      grayscaleParams: { brightnessEnhancement: 150 },
    } as any);
    expect(result.grayscaleParams.brightnessEnhancement).toBe(
      DEFAULT_MODE_PARAMS.brightnessEnhancement,
    );
  });

  it("clamps color brightnessReduction below -100", () => {
    const result = clampConfig({
      colorParams: { brightnessReduction: -200 },
    } as any);
    expect(result.colorParams.brightnessReduction).toBe(
      DEFAULT_MODE_PARAMS.brightnessReduction,
    );
  });

  it("clamps contrast outside range in grayscaleParams", () => {
    const result = clampConfig({
      grayscaleParams: { contrast: 150 },
    } as any);
    expect(result.grayscaleParams.contrast).toBe(DEFAULT_MODE_PARAMS.contrast);
  });

  it("clamps saturation outside range in colorParams", () => {
    const result = clampConfig({
      colorParams: { saturation: -200 },
    } as any);
    expect(result.colorParams.saturation).toBe(
      DEFAULT_MODE_PARAMS.saturation,
    );
  });

  it("keeps valid grayscale params", () => {
    const result = clampConfig({
      grayscaleParams: { contrast: 30, saturation: -10, brightnessEnhancement: 70, brightnessReduction: -40 },
    } as any);
    expect(result.grayscaleParams.contrast).toBe(30);
    expect(result.grayscaleParams.saturation).toBe(-10);
    expect(result.grayscaleParams.brightnessEnhancement).toBe(70);
    expect(result.grayscaleParams.brightnessReduction).toBe(-40);
  });

  it("keeps valid color params", () => {
    const result = clampConfig({
      colorParams: { contrast: 50, saturation: -30, brightnessEnhancement: 60, brightnessReduction: -20 },
    } as any);
    expect(result.colorParams.contrast).toBe(50);
    expect(result.colorParams.saturation).toBe(-30);
    expect(result.colorParams.brightnessEnhancement).toBe(60);
    expect(result.colorParams.brightnessReduction).toBe(-20);
  });

  it("rejects invalid theme", () => {
    const result = clampConfig({ theme: "blue" } as unknown as Partial<AppConfig>);
    expect(result.theme).toBe(DEFAULT_CONFIG.theme);
  });

  it("rejects invalid previewQuality", () => {
    const result = clampConfig({ previewQuality: "ultra" } as unknown as Partial<AppConfig>);
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

  it("rejects invalid colorMode", () => {
    const result = clampConfig({ colorMode: "rgb" } as unknown as Partial<AppConfig>);
    expect(result.colorMode).toBe(DEFAULT_CONFIG.colorMode);
  });

  it("fills in missing fields with defaults", () => {
    const result = clampConfig({ theme: "dark" });
    expect(result.theme).toBe("dark");
    expect(result.grayscaleParams).toEqual(DEFAULT_MODE_PARAMS);
    expect(result.colorParams).toEqual(DEFAULT_MODE_PARAMS);
  });
});
