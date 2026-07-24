export type ThemeMode = "light" | "dark";

export type AppPage = "home" | "preview" | "about";

/** 预览清晰度：低 320 / 中 640 / 高 1280 / 原图(0=不缩小) */
export type PreviewQuality = "low" | "medium" | "high" | "original";

export const PREVIEW_QUALITY_EDGE: Record<PreviewQuality, number> = {
  low: 320,
  medium: 640,
  high: 1280,
  original: 0,
};

export type ColorMode = "grayscale" | "color";

export interface ModeParams {
  brightnessEnhancement: number;
  brightnessReduction: number;
  contrast: number;
  saturation: number;
}

export const DEFAULT_MODE_PARAMS: ModeParams = {
  brightnessEnhancement: 50,
  brightnessReduction: -50,
  contrast: 0,
  saturation: 0,
};

export interface AppConfig {
  grayscaleParams: ModeParams;
  colorParams: ModeParams;
  colorMode: ColorMode;
  exportDirectory: string;
  theme: ThemeMode;
  previewQuality: PreviewQuality;
  /** 是否启用实时效果预览 */
  previewEnabled: boolean;
}

export const DEFAULT_CONFIG: AppConfig = {
  grayscaleParams: { ...DEFAULT_MODE_PARAMS },
  colorParams: { ...DEFAULT_MODE_PARAMS },
  colorMode: "grayscale",
  exportDirectory: "",
  theme: "light",
  previewQuality: "medium",
  previewEnabled: true,
};

export interface ProcessResult {
  outputPath: string;
}

export interface PreviewResult {
  surfacePreview: string;
  innerPreview: string;
}
