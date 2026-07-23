<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount, h } from "vue";
import {
  NButton,
  NCard,
  NSpace,
  NInput,
  NIcon,
  useMessage,
  useNotification,
} from "naive-ui";
import {
  FolderOpenOutline,
  SparklesOutline,
  OpenOutline,
} from "@vicons/ionicons5";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { openPath, revealItemInDir } from "@tauri-apps/plugin-opener";
import ImagePickerCard from "../components/ImagePickerCard.vue";
import BrightnessPanel from "../components/BrightnessPanel.vue";
import EffectPreview from "../components/EffectPreview.vue";
import { useAppConfig } from "../composables/useAppConfig";
import {
  PREVIEW_QUALITY_EDGE,
  type PreviewQuality,
  type PreviewResult,
  type ProcessResult,
} from "../types";

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
const notification = useNotification();
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
const processing = ref(false);

const surfaceEffectUrl = ref<string | null>(null);
const innerEffectUrl = ref<string | null>(null);
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
let previewTimer: ReturnType<typeof setTimeout> | null = null;
let previewSeq = 0;

const previewReady = computed(() => !!surfacePath.value && !!innerPath.value);

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

const canProcess = computed(
  () => !!surfacePath.value && !!innerPath.value && !processing.value,
);

function setEnhancement(v: number) {
  brightnessEnhancement.value = v;
}

function setReduction(v: number) {
  brightnessReduction.value = v;
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

function showExportDoneBanner(outputPath: string) {
  const fileName = outputPath.replace(/\\/g, "/").split("/").pop() || outputPath;
  notification.success({
    title: "合成完成",
    content: fileName,
    meta: outputPath,
    duration: 6500,
    keepAliveOnHover: true,
    action: () =>
      h(
        NButton,
        {
          size: "small",
          secondary: true,
          type: "primary",
          onClick: () => {
            void revealItemInDir(outputPath).catch((e) => {
              message.error(String(e));
            });
          },
        },
        { default: () => "在文件夹中显示" },
      ),
  });
}

async function process() {
  if (!surfacePath.value || !innerPath.value) {
    message.warning("请先选择表图和里图");
    return;
  }
  processing.value = true;
  try {
    const result = await invoke<ProcessResult>("process_phantom_tank", {
      surfacePath: surfacePath.value,
      innerPath: innerPath.value,
      brightnessEnhancement: brightnessEnhancement.value,
      brightnessReduction: brightnessReduction.value,
      exportDirectory: exportDirectory.value || "",
    });
    showExportDoneBanner(result.outputPath);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    notification.error({
      title: "合成失败",
      content: msg || "未知错误",
      duration: 5000,
    });
  } finally {
    processing.value = false;
  }
}

function clearPreview() {
  surfaceEffectUrl.value = null;
  innerEffectUrl.value = null;
  previewError.value = null;
  previewLoading.value = false;
}

async function runPreview() {
  if (!previewEnabled.value || !surfacePath.value || !innerPath.value) {
    clearPreview();
    return;
  }

  const seq = ++previewSeq;
  previewLoading.value = true;
  previewError.value = null;

  try {
    const edge =
      PREVIEW_QUALITY_EDGE[previewQuality.value] ?? PREVIEW_QUALITY_EDGE.medium;
    const result = await invoke<PreviewResult>("preview_phantom_tank", {
      surfacePath: surfacePath.value,
      innerPath: innerPath.value,
      brightnessEnhancement: brightnessEnhancement.value,
      brightnessReduction: brightnessReduction.value,
      maxEdge: edge,
    });
    if (seq !== previewSeq) return;
    surfaceEffectUrl.value = result.surfacePreview;
    innerEffectUrl.value = result.innerPreview;
  } catch (e) {
    if (seq !== previewSeq) return;
    previewError.value = e instanceof Error ? e.message : String(e);
    surfaceEffectUrl.value = null;
    innerEffectUrl.value = null;
  } finally {
    if (seq === previewSeq) {
      previewLoading.value = false;
    }
  }
}

function schedulePreview() {
  if (previewTimer) clearTimeout(previewTimer);
  if (!previewEnabled.value || !surfacePath.value || !innerPath.value) {
    previewSeq += 1;
    clearPreview();
    return;
  }
  previewTimer = setTimeout(() => {
    void runPreview();
  }, 280);
}

function setPreviewQuality(q: PreviewQuality) {
  previewQuality.value = q;
}

function setPreviewEnabled(v: boolean) {
  previewEnabled.value = v;
}

watch(
  [
    surfacePath,
    innerPath,
    brightnessEnhancement,
    brightnessReduction,
    previewQuality,
    previewEnabled,
  ],
  () => schedulePreview(),
  { immediate: true },
);

onBeforeUnmount(() => {
  if (previewTimer) clearTimeout(previewTimer);
  previewSeq += 1;
});
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
          hint="缩略图 / 未点开时显示"
          :box-aspect="sharedBoxAspect"
          @natural-size="onSurfaceNatural"
        />
        <ImagePickerCard
          v-model:path="innerPath"
          title="里图"
          hint="点开原图后显示"
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
