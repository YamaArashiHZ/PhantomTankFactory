import { reactive, toRefs, watch } from "vue";
import { LazyStore } from "@tauri-apps/plugin-store";
import { invoke } from "@tauri-apps/api/core";
import { DEFAULT_CONFIG, type AppConfig, type ThemeMode } from "../types";

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

function clampConfig(raw: Partial<AppConfig> | null | undefined): AppConfig {
  const next = { ...DEFAULT_CONFIG, ...(raw ?? {}) };
  if (
    typeof next.brightnessEnhancement !== "number" ||
    next.brightnessEnhancement < 0 ||
    next.brightnessEnhancement > 100
  ) {
    next.brightnessEnhancement = DEFAULT_CONFIG.brightnessEnhancement;
  }
  if (
    typeof next.brightnessReduction !== "number" ||
    next.brightnessReduction < -100 ||
    next.brightnessReduction > 0
  ) {
    next.brightnessReduction = DEFAULT_CONFIG.brightnessReduction;
  }
  if (next.theme !== "light" && next.theme !== "dark") {
    next.theme = DEFAULT_CONFIG.theme;
  }
  if (typeof next.exportDirectory !== "string") {
    next.exportDirectory = "";
  }
  return next;
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

export function useAppConfig() {
  function setTheme(theme: ThemeMode) {
    state.theme = theme;
  }

  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
  }

  return {
    ...toRefs(state),
    setTheme,
    toggleTheme,
    loadAppConfig,
  };
}
