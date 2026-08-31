<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import {
  NConfigProvider,
  NMessageProvider,
  NNotificationProvider,
  darkTheme,
  type GlobalThemeOverrides,
} from "naive-ui";
import { OverlayScrollbarsComponent } from "overlayscrollbars-vue";
import type { OverlayScrollbars } from "overlayscrollbars";
import "overlayscrollbars/overlayscrollbars.css";
import AppSidebar from "./components/AppSidebar.vue";
import UpdaterBootstrap from "./components/UpdaterBootstrap.vue";
import HomeView from "./views/HomeView.vue";
import AnimateView from "./views/AnimateView.vue";
import PreviewView from "./views/PreviewView.vue";
import AboutView from "./views/AboutView.vue";
import { useAppConfig, loadAppConfig } from "./composables/useAppConfig";
import { isGlobalDragActive, dragHoles } from "./composables/useDragDrop";
import type { AppPage } from "./types";

const holeRects = computed(() => [...dragHoles.values()]);

const page = ref<AppPage>("home");
const { theme, toggleTheme } = useAppConfig();
const ready = ref(false);

/** 滚轮平滑滚动：缓动系数与清理句柄 */
const SMOOTH_EASE = 0.18;
let smoothViewport: HTMLElement | null = null;
let smoothTarget = 0;
let smoothRaf = 0;
let smoothAttached = false;

function clampScroll(el: HTMLElement, y: number) {
  const max = Math.max(0, el.scrollHeight - el.clientHeight);
  return Math.min(max, Math.max(0, y));
}

function smoothTick() {
  const el = smoothViewport;
  if (!el) {
    smoothRaf = 0;
    return;
  }
  const cur = el.scrollTop;
  const diff = smoothTarget - cur;
  if (Math.abs(diff) < 0.4) {
    el.scrollTop = smoothTarget;
    smoothRaf = 0;
    return;
  }
  el.scrollTop = cur + diff * SMOOTH_EASE;
  smoothRaf = requestAnimationFrame(smoothTick);
}

function onSmoothWheel(e: WheelEvent) {
  const el = smoothViewport;
  if (!el) return;
  // 触控板惯性已较平滑时仍统一处理，避免双重滚动
  e.preventDefault();
  let delta = e.deltaY;
  if (e.deltaMode === 1) delta *= 16; // lines
  if (e.deltaMode === 2) delta *= el.clientHeight; // pages
  if (!smoothRaf) smoothTarget = el.scrollTop;
  smoothTarget = clampScroll(el, smoothTarget + delta);
  if (!smoothRaf) smoothRaf = requestAnimationFrame(smoothTick);
}

function onSmoothNativeScroll() {
  // 拖动滑块时同步目标，避免回弹
  if (!smoothRaf && smoothViewport) {
    smoothTarget = smoothViewport.scrollTop;
  }
}

function attachSmoothScroll(os: OverlayScrollbars) {
  detachSmoothScroll();
  const el = os.elements().viewport;
  smoothViewport = el;
  smoothTarget = el.scrollTop;
  el.addEventListener("wheel", onSmoothWheel, { passive: false });
  el.addEventListener("scroll", onSmoothNativeScroll, { passive: true });
  smoothAttached = true;
}

function detachSmoothScroll() {
  if (smoothRaf) {
    cancelAnimationFrame(smoothRaf);
    smoothRaf = 0;
  }
  if (smoothViewport && smoothAttached) {
    smoothViewport.removeEventListener("wheel", onSmoothWheel);
    smoothViewport.removeEventListener("scroll", onSmoothNativeScroll);
  }
  smoothViewport = null;
  smoothAttached = false;
}

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

/** OverlayScrollbars：无箭头、极简细条 */
const osOptions = {
  overflow: {
    x: "hidden" as const,
    y: "scroll" as const,
  },
  scrollbars: {
    theme: "os-theme-minimal",
    visibility: "auto" as const,
    autoHide: "leave" as const,
    autoHideDelay: 600,
    dragScroll: true,
    clickScroll: true,
    pointers: ["mouse", "touch", "pen"] as ("mouse" | "touch" | "pen")[],
  },
};

const osEvents = {
  initialized: (os: OverlayScrollbars) => {
    attachSmoothScroll(os);
  },
  destroyed: () => {
    detachSmoothScroll();
  },
};

onMounted(async () => {
  await loadAppConfig();
  ready.value = true;
});

onBeforeUnmount(() => {
  detachSmoothScroll();
});
</script>

<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="themeOverrides" style="height: 100%">
    <n-notification-provider placement="bottom" :max="3" container-class="app-notify-bottom">
      <n-message-provider>
        <UpdaterBootstrap v-if="ready" />
        <div
          v-if="ready"
          class="app-shell"
          :class="theme === 'dark' ? 'theme-dark' : 'theme-light'"
          :style="shellStyle"
        >
          <AppSidebar
            :current="page"
            :theme="theme"
            @navigate="(p) => (page = p)"
            @toggle-theme="toggleTheme"
          />
          <OverlayScrollbarsComponent
            class="app-main"
            defer
            :options="osOptions"
            :events="osEvents"
          >
            <div class="app-main-inner">
              <Transition name="page" mode="out-in">
                <HomeView v-if="page === 'home'" key="home" />
                <AnimateView v-else-if="page === 'animate'" key="animate" />
                <PreviewView v-else-if="page === 'preview'" key="preview" />
                <AboutView v-else key="about" />
              </Transition>
            </div>
          </OverlayScrollbarsComponent>
        </div>
      </n-message-provider>
    </n-notification-provider>
  </n-config-provider>

  <Teleport to="body">
    <svg
      v-if="isGlobalDragActive"
      class="drag-shield"
      width="100%"
      height="100%"
    >
      <defs>
        <mask id="drag-shield-mask">
          <rect width="100%" height="100%" fill="white" />
          <rect
            v-for="(hole, i) in holeRects"
            :key="i"
            :x="hole.x"
            :y="hole.y"
            :width="hole.w"
            :height="hole.h"
            rx="12"
            fill="black"
          />
        </mask>
      </defs>
      <rect
        width="100%"
        height="100%"
        fill="rgba(0, 0, 0, 0.25)"
        mask="url(#drag-shield-mask)"
      />
    </svg>
  </Teleport>
</template>

<style>
/* 底部横幅式通知，类似手机通知条 */
.app-notify-bottom,
.n-notification-container--bottom {
  left: 50% !important;
  right: auto !important;
  transform: translateX(-50%);
  width: min(560px, calc(100vw - 32px));
  bottom: 20px !important;
  align-items: stretch !important;
}

.app-notify-bottom .n-notification,
.n-notification-container--bottom .n-notification {
  width: 100% !important;
  max-width: 100% !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
  border-radius: 14px !important;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.18) !important;
}

/* —— OverlayScrollbars 极简主题 —— */
.app-main.os-host,
.app-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.app-main-inner {
  padding: 20px 24px 24px;
  width: 100%;
  box-sizing: border-box;
}

.app-main-inner > * {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

/* 页面切换：淡出 + 轻微位移 */
.page-enter-active,
.page-leave-active {
  transition:
    opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.page-enter-to,
.page-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* 极简滚动条：固定 10px */
.os-theme-minimal {
  --os-size: 10px;
  --os-padding-perpendicular: 3px;
  --os-padding-axis: 6px;
  --os-track-border-radius: 999px;
  --os-handle-border-radius: 999px;
  --os-handle-bg: rgba(71, 85, 105, 0.42);
  --os-handle-bg-hover: rgba(71, 85, 105, 0.62);
  --os-handle-bg-active: rgba(51, 65, 85, 0.78);
  --os-handle-border: 0;
  --os-handle-border-hover: none;
  --os-handle-border-active: none;
  --os-handle-min-size: 32px;
}

/* 深色模式：更亮、对比更强 */
.theme-dark .os-theme-minimal {
  --os-handle-bg: rgba(226, 232, 240, 0.38);
  --os-handle-bg-hover: rgba(241, 245, 249, 0.55);
  --os-handle-bg-active: rgba(248, 250, 252, 0.72);
}

.os-theme-minimal .os-scrollbar-track {
  background: transparent !important;
}

.os-theme-minimal .os-scrollbar-handle {
  transition:
    background 0.2s ease,
    opacity 0.2s ease;
}
</style>

<style>
.drag-shield {
  position: fixed;
  inset: 0;
  z-index: 10000;
  pointer-events: none;
  animation: shield-fade 0.15s ease;
}

@keyframes shield-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
