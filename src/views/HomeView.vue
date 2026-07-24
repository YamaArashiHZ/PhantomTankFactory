<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  NButton,
  NCard,
  NSpace,
  NInput,
  NIcon,
  useMessage,
} from "naive-ui";
import {
  FolderOpenOutline,
  SparklesOutline,
  OpenOutline,
} from "@vicons/ionicons5";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { openPath } from "@tauri-apps/plugin-opener";
import ImagePickerCard from "../components/ImagePickerCard.vue";
import BrightnessPanel from "../components/BrightnessPanel.vue";
import EffectPreview from "../components/EffectPreview.vue";
import { useAppConfig } from "../composables/useAppConfig";
import { useEffectPreview } from "../composables/useEffectPreview";
import { useExport } from "../composables/useExport";
import type { PreviewQuality } from "../types";

/** 横/竖比例上限 16:9 → 宽高比夹在 9:16 ~ 16:9 */
const ASPECT_MAX = 16 / 9;
const ASPECT_MIN = 9 / 16;
const DEFAULT_ASPECT = 16 / 9;

type NaturalSize = { width: number; height: number };

function clampAspect(width: number, height: number): number {
  const raw = width / height;
  return Math.min(ASPECT_MAX, Math.max(ASPECT_MIN, raw));
}

const message = useMessage();
const {
  brightnessEnhancement,
  brightnessReduction,
  exportDirectory,
  previewQuality,
  previewEnabled,
} = useAppConfig();

const surfacePath = ref<string | null>(null);
const innerPath = ref<string | null>(null);
const surfaceNatural = ref<NaturalSize | null>(null);
const innerNatural = ref<NaturalSize | null>(null);

/**
 * 两卡同步比例：各自 clamp 后取「更高」的一方（aspect 更小），
 * 即容器尺寸取 max，保证竖图够大且两侧同高。
 */
const sharedBoxAspect = computed(() => {
  const aspects: number[] = [];
  if (surfaceNatural.value) {
    aspects.push(clampAspect(surfaceNatural.value.width, surfaceNatural.value.height));
  }
  if (innerNatural.value) {
    aspects.push(clampAspect(innerNatural.value.width, innerNatural.value.height));
  }
  if (aspects.length === 0) return DEFAULT_ASPECT;
  return Math.min(...aspects);
});

watch(surfacePath, (p) => {
  if (!p) surfaceNatural.value = null;
});
watch(innerPath, (p) => {
  if (!p) innerNatural.value = null;
});

function onSurfaceNatural(s: NaturalSize | null) {
  surfaceNatural.value = s;
}

function onInnerNatural(s: NaturalSize | null) {
  innerNatural.value = s;
}

const {
  surfaceEffectUrl,
  innerEffectUrl,
  previewLoading,
  previewError,
  previewReady,
} = useEffectPreview(surfacePath, innerPath);

const { processing, canProcess, process } = useExport(surfacePath, innerPath);

function setEnhancement(v: number) {
  brightnessEnhancement.value = v;
}

function setReduction(v: number) {
  brightnessReduction.value = v;
}

function setPreviewQuality(q: PreviewQuality) {
  previewQuality.value = q;
}

function setPreviewEnabled(v: boolean) {
  previewEnabled.value = v;
}

async function pickExportDir() {
  const dir = await open({ directory: true, multiple: false });
  if (typeof dir === "string") {
    exportDirectory.value = dir;
  }
}

async function openExportDir() {
  try {
    let dir = exportDirectory.value?.trim() || "";
    if (!dir) {
      dir = await invoke<string>("get_temp_dir");
    }
    await openPath(dir);
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e));
  }
}
</script>

<template>
  <div class="home">
    <h1 class="page-title">幻影坦克合成</h1>
    <p class="page-subtitle">
      选择表图（缩略图可见）与里图（点开大图可见），调整亮度后导出 PNG。
    </p>

    <n-space vertical :size="16" style="width: 100%">
      <div class="pickers">
        <ImagePickerCard
          v-model:path="surfacePath"
          title="表图"
          hint="拖放或点击选择表图"
          :box-aspect="sharedBoxAspect"
          @natural-size="onSurfaceNatural"
        />
        <ImagePickerCard
          v-model:path="innerPath"
          title="里图"
          hint="拖放或点击选择里图"
          :box-aspect="sharedBoxAspect"
          @natural-size="onInnerNatural"
        />
      </div>

      <BrightnessPanel
        :enhancement="brightnessEnhancement"
        :reduction="brightnessReduction"
        @update:enhancement="setEnhancement"
        @update:reduction="setReduction"
      />

      <EffectPreview
        :surface-preview="surfaceEffectUrl"
        :inner-preview="innerEffectUrl"
        :loading="previewLoading"
        :ready="previewReady"
        :error="previewError"
        :quality="previewQuality"
        :enabled="previewEnabled"
        @update:quality="setPreviewQuality"
        @update:enabled="setPreviewEnabled"
      />

      <n-card title="导出" size="small">
        <n-space vertical :size="12" style="width: 100%">
          <div class="export-row">
            <n-input
              v-model:value="exportDirectory"
              placeholder="导出目录（留空则使用临时目录）"
              clearable
            />
            <n-button secondary @click="pickExportDir">
              <template #icon>
                <n-icon :component="FolderOpenOutline" />
              </template>
              浏览
            </n-button>
            <n-button secondary @click="openExportDir">
              <template #icon>
                <n-icon :component="OpenOutline" />
              </template>
              打开目录
            </n-button>
          </div>

          <n-space>
            <n-button
              type="primary"
              size="large"
              :disabled="!canProcess"
              :loading="processing"
              @click="process"
            >
              <template #icon>
                <n-icon :component="SparklesOutline" />
              </template>
              生成幻影坦克
            </n-button>
          </n-space>
        </n-space>
      </n-card>
    </n-space>
  </div>
</template>

<style scoped>
.home {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.home :deep(.n-space) {
  width: 100%;
}

.home :deep(.n-card) {
  width: 100%;
}

.pickers {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
  width: 100%;
}

.pickers > * {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.export-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

@media (max-width: 720px) {
  .pickers {
    grid-template-columns: 1fr;
  }
}
</style>
