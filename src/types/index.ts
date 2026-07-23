export type ThemeMode = "light" | "dark";

export type AppPage = "home" | "about";

export interface AppConfig {
  brightnessEnhancement: number;
  brightnessReduction: number;
  exportDirectory: string;
  theme: ThemeMode;
}

export const DEFAULT_CONFIG: AppConfig = {
  brightnessEnhancement: 50,
  brightnessReduction: -50,
  exportDirectory: "",
  theme: "light",
};

export interface ProcessResult {
  outputPath: string;
}
