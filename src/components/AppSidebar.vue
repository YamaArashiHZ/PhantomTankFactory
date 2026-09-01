<script setup lang="ts">
import { NButton, NTooltip, NIcon } from "naive-ui";
import {
  HomeOutline,
  ImagesOutline,
  FilmOutline,
  InformationCircleOutline,
  MoonOutline,
  SunnyOutline,
} from "@vicons/ionicons5";
import type { AppPage, ThemeMode } from "../types";

defineProps<{
  current: AppPage;
  theme: ThemeMode;
}>();

const emit = defineEmits<{
  navigate: [page: AppPage];
  toggleTheme: [];
}>();
</script>

<template>
  <aside class="sidebar">
    <div class="brand" title="PhantomTank Factory">PTF</div>

    <nav class="nav-top">
      <n-tooltip placement="right" :delay="400">
        <template #trigger>
          <n-button
            quaternary
            circle
            size="large"
            :type="current === 'home' ? 'primary' : 'default'"
            :class="{ active: current === 'home' }"
            @click="emit('navigate', 'home')"
          >
            <template #icon>
              <n-icon :component="HomeOutline" :size="22" />
            </template>
          </n-button>
        </template>
        主页
      </n-tooltip>

      <n-tooltip placement="right" :delay="400">
        <template #trigger>
          <n-button
            quaternary
            circle
            size="large"
            :type="current === 'animate' ? 'primary' : 'default'"
            :class="{ active: current === 'animate' }"
            @click="emit('navigate', 'animate')"
          >
            <template #icon>
              <n-icon :component="FilmOutline" :size="22" />
            </template>
          </n-button>
        </template>
        动图合成
      </n-tooltip>

      <n-tooltip placement="right" :delay="400">
        <template #trigger>
          <n-button
            quaternary
            circle
            size="large"
            :type="current === 'preview' ? 'primary' : 'default'"
            :class="{ active: current === 'preview' }"
            @click="emit('navigate', 'preview')"
          >
            <template #icon>
              <n-icon :component="ImagesOutline" :size="22" />
            </template>
          </n-button>
        </template>
        效果查看
      </n-tooltip>

      <n-tooltip placement="right" :delay="400">
        <template #trigger>
          <n-button
            quaternary
            circle
            size="large"
            :type="current === 'about' ? 'primary' : 'default'"
            :class="{ active: current === 'about' }"
            @click="emit('navigate', 'about')"
          >
            <template #icon>
              <n-icon :component="InformationCircleOutline" :size="22" />
            </template>
          </n-button>
        </template>
        关于
      </n-tooltip>
    </nav>

    <div class="nav-bottom">
      <n-tooltip placement="right" :delay="400">
        <template #trigger>
          <n-button quaternary circle size="large" @click="emit('toggleTheme')">
            <template #icon>
              <n-icon :component="theme === 'dark' ? SunnyOutline : MoonOutline" :size="22" />
            </template>
          </n-button>
        </template>
        {{ theme === "dark" ? "切换浅色" : "切换深色" }}
      </n-tooltip>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--nav-width);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 0;
  gap: 8px;
  border-right: 1px solid var(--border-color);
  background: var(--sidebar-bg);
}

.brand {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #fff;
  background: linear-gradient(135deg, #4f7cff 0%, #7b5cff 100%);
  margin-bottom: 10px;
  user-select: none;
}

.nav-top {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.nav-bottom {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.active {
  background: var(--nav-active-bg) !important;
}
</style>
