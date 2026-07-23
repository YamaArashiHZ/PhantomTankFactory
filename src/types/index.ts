export type ThemeMode = "light" | "dark";

export type AppPage = "home" | "about";

/** 预览清晰度：低 320 / 中 640 / 高 1280 / 原图(0=不缩小) */
export type PreviewQuality = "low" | "medium" | "high" | "original";

export const PREVIEW_QUALITY_EDGE: Record<PreviewQuality, number> = {
  low: 320,
  medium: 640,
  high: 1280,
  original: 0,
};

export interface AppConfig {
  brightnessEnhancement: number;
  brightnessReduction: number;
  exportDirectory: string;
  theme: ThemeMode;
  previewQuality: PreviewQuality;
  /** 是否启用实时效果预览 */
  previewEnabled: boolean;
}

export const DEFAULT_CONFIG: AppConfig = {
  brightnessEnhancement: 50,
  brightnessReduction: -50,
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
