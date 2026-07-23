<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  NConfigProvider,
  NMessageProvider,
  darkTheme,
  type GlobalThemeOverrides,
} from "naive-ui";
import AppSidebar from "./components/AppSidebar.vue";
import HomeView from "./views/HomeView.vue";
import AboutView from "./views/AboutView.vue";
import { useAppConfig, loadAppConfig } from "./composables/useAppConfig";
import type { AppPage } from "./types";

const page = ref<AppPage>("home");
const { theme, toggleTheme } = useAppConfig();
const ready = ref(false);

const naiveTheme = computed(() => (theme.value === "dark" ? darkTheme : null));

const themeOverrides = computed<GlobalThemeOverrides>(() => {
  const isDark = theme.value === "dark";
  return {
    common: {
      borderRadius: "10px",
      fontFamily: "var(--app-font)",
      primaryColor: "#5b7cfa",
      primaryColorHover: "#6e8cff",
      primaryColorPressed: "#4a6ae0",
      primaryColorSuppl: "#5b7cfa",
    },
    Card: {
      borderRadius: "14px",
      color: isDark ? "rgba(30, 32, 40, 0.92)" : "rgba(255, 255, 255, 0.92)",
      borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(15, 23, 42, 0.08)",
    },
  };
});

const shellStyle = computed(() => {
  const isDark = theme.value === "dark";
  return {
    "--sidebar-bg": isDark ? "rgba(18, 20, 28, 0.96)" : "rgba(248, 250, 252, 0.96)",
    "--border-color": isDark ? "rgba(255,255,255,0.08)" : "rgba(15, 23, 42, 0.08)",
    "--nav-active-bg": isDark ? "rgba(91, 124, 250, 0.22)" : "rgba(91, 124, 250, 0.14)",
    "--preview-bg": isDark ? "rgba(0,0,0,0.25)" : "rgba(15, 23, 42, 0.03)",
    "--primary-soft": "#5b7cfa",
    "--main-bg": isDark
      ? "radial-gradient(1200px 600px at 10% -10%, #1a2240 0%, #12141c 45%, #0e1016 100%)"
      : "radial-gradient(1200px 600px at 10% -10%, #e8eeff 0%, #f4f7fb 40%, #eef2f7 100%)",
    color: isDark ? "#e8eaef" : "#1c2333",
    background: "var(--main-bg)",
  } as Record<string, string>;
});

onMounted(async () => {
  await loadAppConfig();
  ready.value = true;
});
</script>

<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="themeOverrides" style="height: 100%">
    <n-message-provider>
      <div v-if="ready" class="app-shell" :style="shellStyle">
        <AppSidebar
          :current="page"
          :theme="theme"
          @navigate="(p) => (page = p)"
          @toggle-theme="toggleTheme"
        />
        <main class="app-main">
          <HomeView v-if="page === 'home'" />
          <AboutView v-else />
        </main>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>
