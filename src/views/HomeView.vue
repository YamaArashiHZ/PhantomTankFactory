<script setup lang="ts">
import { ref, computed } from "vue";
import {
  NButton,
  NCard,
  NSpace,
  NInput,
  NText,
  NAlert,
  NSpin,
  NIcon,
  useMessage,
} from "naive-ui";
import { FolderOpenOutline, SparklesOutline, CheckmarkCircleOutline } from "@vicons/ionicons5";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import ImagePickerCard from "../components/ImagePickerCard.vue";
import BrightnessPanel from "../components/BrightnessPanel.vue";
import { useAppConfig } from "../composables/useAppConfig";
import type { ProcessResult } from "../types";

const message = useMessage();
const { brightnessEnhancement, brightnessReduction, exportDirectory } = useAppConfig();

const surfacePath = ref<string | null>(null);
const innerPath = ref<string | null>(null);
const processing = ref(false);
const lastOutput = ref<string | null>(null);

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

async function process() {
  if (!surfacePath.value || !innerPath.value) {
    message.warning("请先选择表图和里图");
    return;
  }
  processing.value = true;
  lastOutput.value = null;
  try {
    const result = await invoke<ProcessResult>("process_phantom_tank", {
      surfacePath: surfacePath.value,
      innerPath: innerPath.value,
      brightnessEnhancement: brightnessEnhancement.value,
      brightnessReduction: brightnessReduction.value,
      exportDirectory: exportDirectory.value || "",
    });
    lastOutput.value = result.outputPath;
    message.success("合成完成");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    message.error(msg || "合成失败");
  } finally {
    processing.value = false;
  }
}

async function revealOutput() {
  if (!lastOutput.value) return;
  try {
    await revealItemInDir(lastOutput.value);
  } catch (e) {
    message.error(String(e));
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
          hint="缩略图 / 未点开时显示"
        />
        <ImagePickerCard
          v-model:path="innerPath"
          title="里图"
          hint="点开原图后显示"
        />
      </div>

      <BrightnessPanel
        :enhancement="brightnessEnhancement"
        :reduction="brightnessReduction"
        @update:enhancement="setEnhancement"
        @update:reduction="setReduction"
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

          <n-spin v-if="processing" description="正在合成，请稍候…" />

          <n-alert v-if="lastOutput" type="success" :bordered="false">
            <template #icon>
              <n-icon :component="CheckmarkCircleOutline" />
            </template>
            <div class="result-row">
              <n-text class="result-path" :title="lastOutput">{{ lastOutput }}</n-text>
              <n-button size="small" secondary @click="revealOutput">在文件夹中显示</n-button>
            </div>
          </n-alert>
        </n-space>
      </n-card>
    </n-space>
  </div>
</template>

<style scoped>
.home {
  max-width: 980px;
}

.pickers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.export-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.result-path {
  flex: 1;
  min-width: 0;
  word-break: break-all;
  font-size: 12px;
}

@media (max-width: 720px) {
  .pickers {
    grid-template-columns: 1fr;
  }
}
</style>
