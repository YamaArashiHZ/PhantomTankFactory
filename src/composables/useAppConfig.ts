import { computed, reactive, toRefs, watch } from "vue";
import { LazyStore } from "@tauri-apps/plugin-store";
import { invoke } from "@tauri-apps/api/core";
import {
  DEFAULT_CONFIG,
  DEFAULT_MODE_PARAMS,
  type AppConfig,
  type ModeParams,
  type ThemeMode,
} from "../types";

const STORE_FILE = "settings.json";
const STORE_KEY = "appConfig";

let store: LazyStore | null = null;
let loaded = false;

const state = reactive<AppConfig>({ ...DEFAULT_CONFIG });

function getStore() {
  if (!store) {
    store = new LazyStore(STORE_FILE);
  }
  return store;
}

function clampModeParams(
  raw: Partial<ModeParams> | undefined,
): ModeParams {
  const p = { ...DEFAULT_MODE_PARAMS, ...(raw ?? {}) };
  if (
    typeof p.brightnessEnhancement !== "number" ||
    p.brightnessEnhancement < 0 ||
    p.brightnessEnhancement > 100
  ) {
    p.brightnessEnhancement = DEFAULT_MODE_PARAMS.brightnessEnhancement;
  }
  if (
    typeof p.brightnessReduction !== "number" ||
    p.brightnessReduction < -100 ||
    p.brightnessReduction > 0
  ) {
    p.brightnessReduction = DEFAULT_MODE_PARAMS.brightnessReduction;
  }
  if (
    typeof p.contrast !== "number" ||
    p.contrast < -100 ||
    p.contrast > 100
  ) {
    p.contrast = DEFAULT_MODE_PARAMS.contrast;
  }
  if (
    typeof p.saturation !== "number" ||
    p.saturation < -100 ||
    p.saturation > 100
  ) {
    p.saturation = DEFAULT_MODE_PARAMS.saturation;
  }
  return p;
}

export function clampConfig(
  raw: Partial<AppConfig> | null | undefined,
): AppConfig {
  const flat = { ...DEFAULT_CONFIG, ...(raw ?? {}) };
  flat.grayscaleParams = clampModeParams((raw as any)?.grayscaleParams);
  flat.colorParams = clampModeParams((raw as any)?.colorParams);
  if (flat.theme !== "light" && flat.theme !== "dark") {
    flat.theme = DEFAULT_CONFIG.theme;
  }
  const cm = flat.colorMode as string;
  if (cm !== "grayscale" && cm !== "color") {
    flat.colorMode = DEFAULT_CONFIG.colorMode;
  }
  if (typeof flat.exportDirectory !== "string") {
    flat.exportDirectory = "";
  }
  const q = flat.previewQuality as string;
  if (q !== "low" && q !== "medium" && q !== "high" && q !== "original") {
    flat.previewQuality = DEFAULT_CONFIG.previewQuality;
  }
  if (typeof flat.previewEnabled !== "boolean") {
    flat.previewEnabled = DEFAULT_CONFIG.previewEnabled;
  }
  return flat;
}

export async function loadAppConfig() {
  if (loaded) return;
  try {
    const s = getStore();
    const raw = await s.get<Partial<AppConfig>>(STORE_KEY);
    const cfg = clampConfig(raw);
    Object.assign(state, cfg);

    if (!state.exportDirectory) {
      try {
        const def = await invoke<string>("get_default_export_dir");
        state.exportDirectory = def;
      } catch {
        /* ignore */
      }
    }
  } catch {
    Object.assign(state, DEFAULT_CONFIG);
  } finally {
    loaded = true;
  }
}

async function persist() {
  if (!loaded) return;
  try {
    const s = getStore();
    await s.set(STORE_KEY, { ...state });
    await s.save();
  } catch {
    /* ignore */
  }
}

watch(state, () => {
  void persist();
}, { deep: true });

function activeParams() {
  return state.colorMode === "color"
    ? state.colorParams
    : state.grayscaleParams;
}

export function useAppConfig() {
  function setTheme(theme: ThemeMode) {
    state.theme = theme;
  }

  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
  }

  const brightnessEnhancement = computed({
    get: () => activeParams().brightnessEnhancement,
    set: (v) => {
      activeParams().brightnessEnhancement = v;
    },
  });

  const brightnessReduction = computed({
    get: () => activeParams().brightnessReduction,
    set: (v) => {
      activeParams().brightnessReduction = v;
    },
  });

  const contrast = computed({
    get: () => activeParams().contrast,
    set: (v) => {
      activeParams().contrast = v;
    },
  });

  const saturation = computed({
    get: () => activeParams().saturation,
    set: (v) => {
      activeParams().saturation = v;
    },
  });

  const simpleRefs = toRefs(state);

  return {
    brightnessEnhancement,
    brightnessReduction,
    contrast,
    saturation,
    colorMode: simpleRefs.colorMode,
    exportDirectory: simpleRefs.exportDirectory,
    theme: simpleRefs.theme,
    previewQuality: simpleRefs.previewQuality,
    previewEnabled: simpleRefs.previewEnabled,
    setTheme,
    toggleTheme,
    loadAppConfig,
  };
}
