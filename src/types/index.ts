export type ThemeMode = "light" | "dark";

export type AppPage = "home" | "animate" | "preview" | "about";

/** APNG 播放方式：无限循环 / 仅一次 / 自定义次数 */
export type ApngLoop = "infinite" | "once" | "times";

/** 里图帧：路径 + 独立显示时长(ms) */
export interface ApngInnerFrame {
  /** 稳定 id，用于拖拽排序时保持 DOM 身份 */
  id: string;
  path: string | null;
  delayMs: number;
}

/** process_apng 返回 */
export interface ApngResult {
  outputPath: string;
  sizeKb: number;
  warning: string | null;
}

/** preview_apng 返回 */
export interface ApngPreviewResult {
  /** 每帧 PNG data URL 列表 */
  frames: string[];
}

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
