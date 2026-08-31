<script setup lang="ts">
import { ref, watch } from "vue";
import {
  NCard,
  NSpace,
  NInputNumber,
  NInput,
  NButton,
  NIcon,
  NSelect,
  NSlider,
  NSwitch,
  NText,
  NEmpty,
  NSpin,
  useMessage,
} from "naive-ui";
import {
  FilmOutline,
  FolderOpenOutline,
  OpenOutline,
  AddOutline,
  ReorderThreeOutline,
  SparklesOutline,
} from "@vicons/ionicons5";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { openPath } from "@tauri-apps/plugin-opener";
import ImagePickerCard from "../components/ImagePickerCard.vue";
import { useApng } from "../composables/useApng";
import { useDragDrop } from "../composables/useDragDrop";
import type { ApngLoop } from "../types";

const message = useMessage();
const {
  surfacePath,
  surfaceDelayMs,
  unifiedDelay,
  unifiedDelayMs,
  innerFrames,
  loop,
  times,
  compression,
  grayscale,
  maxSizeKb,
  processing,
  previewing,
  previewUrl,
  previewError,
  canProcess,
  filledInners,
  addInner,
  removeInner,
  reorderInner,
  schedulePreview,
  process,
  exportDirectory,
} = useApng();

const loopOptions: { label: string; value: ApngLoop }[] = [
  { label: "无限循环", value: "infinite" },
  { label: "仅一次", value: "once" },
  { label: "指定次数", value: "times" },
];

const dragIndex = ref<number | null>(null);
function onDragStart(i: number) {
  dragIndex.value = i;
}
function onDrop(i: number) {
  if (dragIndex.value !== null && dragIndex.value !== i) {
    reorderInner(dragIndex.value, i);
  }
  dragIndex.value = null;
}

/** 滚轮在横向滚动区优先横向滚动，并阻止冒泡到上层平滑滚动容器 */
function onInnerWheel(e: WheelEvent) {
  const el = e.currentTarget as HTMLElement;
  if (!el || el.scrollWidth <= el.clientWidth) return;
  e.preventDefault();
  e.stopPropagation();
  el.scrollLeft += e.deltaY;
}

/** 添加区：可点击添加空卡，也可直接拖入图片 */
const addSlotRef = ref<HTMLElement | null>(null);
const { isDragOver: addDragOver } = useDragDrop(addSlotRef, (path) =>
  addInner(path),
);

watch(
  [
    surfacePath,
    surfaceDelayMs,
    unifiedDelay,
    unifiedDelayMs,
    innerFrames,
    loop,
    times,
    compression,
    grayscale,
  ],
  () => schedulePreview(),
  { deep: true },
);

async function pickExportDir() {
  const dir = await open({ directory: true, multiple: false });
  if (typeof dir === "string") exportDirectory.value = dir;
}
async function openExportDir() {
  try {
    let dir = exportDirectory.value?.trim() || "";
    if (!dir) dir = await invoke<string>("get_temp_dir");
    await openPath(dir);
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e));
  }
}
</script>

<template>
  <div class="animate">
    <h1 class="page-title">动图合成（APNG）</h1>
    <p class="page-subtitle">
      选择表图（首帧封面）与若干里图，按每帧时长合成可循环播放的 APNG 动图。
    </p>

    <n-space vertical :size="16" style="width: 100%">
      <!-- 表图 + 里图 选择区 -->
      <n-card size="small">
        <div class="apng-pickers">
          <!-- 表图（固定） -->
          <div class="surface-pane">
            <div class="pane-title">表图</div>
            <ImagePickerCard
              v-model:path="surfacePath"
              title="表图"
              hint="拖放或点击选择表图"
              :box-aspect="1"
              preview-fit="cover"
            />
            <div class="delay-row">
              <n-text depth="3" class="delay-label">显示时间</n-text>
              <n-input-number
                v-model:value="surfaceDelayMs"
                :min="50"
                :max="60000"
                :step="100"
                size="small"
                :show-button="false"
                class="delay-input"
              />
              <span class="unit">ms</span>
            </div>
          </div>

          <!-- 里图（横向滚动） -->
          <div class="inner-pane">
            <div class="pane-header">
              <div class="pane-title">里图</div>
              <div class="header-right">
                <div v-if="unifiedDelay" class="delay-row header-delay">
                  <n-input-number
                    v-model:value="unifiedDelayMs"
                    :min="50"
                    :max="60000"
                    :step="100"
                    size="small"
                    :show-button="false"
                    class="delay-input"
                  />
                  <span class="unit">ms</span>
                </div>
                <div class="unified-toggle">
                  <n-text depth="3">统一显示时间</n-text>
                  <n-switch v-model:value="unifiedDelay" />
                </div>
              </div>
            </div>

            <div class="inner-row" @wheel="onInnerWheel">
              <div v-for="(frame, i) in innerFrames" :key="i" class="inner-slot">
                <ImagePickerCard
                  v-model:path="frame.path"
                  :title="`里图 ${i + 1}`"
                  hint="拖放或点击选择"
                  :box-aspect="1"
                  preview-fit="cover"
                  always-show-clear
                  @clear="removeInner(i)"
                />
                <div class="delay-row slot-delay">
                  <span
                    class="drag-handle"
                    title="拖动排序"
                    draggable="true"
                    @dragstart="onDragStart(i)"
                    @dragover.prevent
                    @drop="onDrop(i)"
                  >
                    <n-icon :component="ReorderThreeOutline" :size="16" />
                  </span>
                  <template v-if="!unifiedDelay">
                    <n-text depth="3" class="delay-label">显示时间</n-text>
                    <n-input-number
                      v-model:value="frame.delayMs"
                      :min="50"
                      :max="60000"
                      :step="100"
                      size="small"
                      :show-button="false"
                      class="delay-input"
                    />
                    <span class="unit">ms</span>
                  </template>
                </div>
              </div>

              <!-- 添加里图（卡片样式，可拖入图片） -->
              <div
                ref="addSlotRef"
                class="inner-slot add-slot"
                :class="{ 'drag-over': addDragOver }"
                @click="addInner()"
              >
                <div class="add-box">
                  <n-icon :component="AddOutline" :size="26" />
                  <n-text depth="3" class="add-label">添加里图（可拖入图片）</n-text>
                </div>
              </div>
            </div>
          </div>
        </div>
      </n-card>

      <!-- 参数 -->
      <n-card title="播放与压缩" size="small">
        <n-space vertical :size="14" style="width: 100%">
          <div class="param-row">
            <n-text depth="3" style="width: 88px">循环方式</n-text>
            <n-select
              v-model:value="loop"
              :options="loopOptions"
              size="small"
              style="width: 200px"
            />
          </div>

          <div v-if="loop === 'times'" class="param-row">
            <n-text depth="3" style="width: 88px">播放次数</n-text>
            <n-input-number
              v-model:value="times"
              :min="1"
              :max="999"
              size="small"
              style="width: 140px"
            />
            <span class="unit">次</span>
          </div>

          <div class="param-row">
            <n-text depth="3" style="width: 88px">压缩等级</n-text>
            <n-slider
              v-model:value="compression"
              :min="0"
              :max="9"
              :step="1"
              :marks="{ 0: '0', 9: '9' }"
              style="flex: 1; margin: 0 12px"
            />
            <n-text depth="3">{{ compression }}</n-text>
          </div>

          <div class="param-row">
            <n-text depth="3" style="width: 88px">灰度量化</n-text>
            <n-switch v-model:value="grayscale" />
            <n-text depth="3" class="hint">开启可显著减小体积（有损）</n-text>
          </div>

          <div class="param-row">
            <n-text depth="3" style="width: 88px">大小上限</n-text>
            <n-input-number
              :value="maxSizeKb ?? 0"
              :min="0"
              :max="102400"
              size="small"
              style="width: 200px"
              placeholder="不限制"
              @update:value="(v: number | null) => (maxSizeKb = v && v > 0 ? v : null)"
            />
            <span class="unit">KB（0/空 = 不限制）</span>
          </div>
        </n-space>
      </n-card>

      <!-- 预览 -->
      <n-card title="预览" size="small">
        <div class="preview-box">
          <img
            v-if="previewUrl"
            :src="previewUrl"
            alt="APNG 预览"
            class="preview-img"
          />
          <n-spin v-else-if="previewing" size="small" />
          <n-empty
            v-else
            size="small"
            :description="previewError || '选择表图与至少 1 张里图后自动生成预览'"
          />
        </div>
      </n-card>

      <!-- 导出 -->
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

          <div class="export-action">
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
              生成 APNG
            </n-button>
            <n-text depth="3">
              {{ filledInners }} 张里图，共 {{ innerFrames.length + 1 }} 帧
            </n-text>
            <n-icon :component="FilmOutline" :size="18" />
          </div>
        </n-space>
      </n-card>
    </n-space>
  </div>
</template>

<style scoped>
.animate {
  width: 100%;
  box-sizing: border-box;
}
.animate :deep(.n-card) {
  width: 100%;
}

/* —— 表图/里图选择区 —— */
.apng-pickers {
  display: flex;
  gap: 18px;
  width: 100%;
  align-items: flex-start;
}

.surface-pane {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.inner-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pane-title {
  font-size: 14px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-delay {
  margin: 0;
}

.unified-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

/* 里图横向滚动 + 细滚动条（靠底） */
.inner-row {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
  align-items: flex-start;
}
.inner-row::-webkit-scrollbar {
  height: 4px;
}
.inner-row::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.42);
  border-radius: 999px;
}
.inner-row::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.62);
}
.inner-row::-webkit-scrollbar-track {
  background: transparent;
}

.inner-slot {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.drag-handle {
  display: inline-flex;
  align-items: center;
  cursor: grab;
  color: var(--n-text-color-3, #999);
  user-select: none;
}

.delay-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.slot-delay {
  margin-top: 2px;
}
.delay-label {
  font-size: 12px;
  flex-shrink: 0;
}
.delay-input {
  width: 120px;
}
.unit {
  color: var(--n-text-color-3, #999);
  font-size: 12px;
}
.hint {
  font-size: 12px;
}

/* 添加里图：卡片样式、可拖入 */
.add-slot {
  cursor: pointer;
  width: 220px;
}
.add-box {
  width: 100%;
  aspect-ratio: 1 / 1;
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  background: var(--preview-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--n-text-color-3, #999);
  transition: border-color 0.2s, background 0.2s;
}
.add-slot:hover .add-box,
.add-slot.drag-over .add-box {
  border-color: var(--primary-soft);
  border-style: solid;
  background: rgba(91, 124, 250, 0.08);
}
.add-label {
  text-align: center;
  font-size: 12px;
  padding: 0 8px;
}

/* 参数/导出等行 */
.param-row,
.export-row,
.export-action {
  display: flex;
  align-items: center;
  gap: 10px;
}
.export-row {
  width: 100%;
}
.export-row .n-input {
  flex: 1 1 auto;
}
.export-action {
  gap: 12px;
}

/* 预览 */
.preview-box {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  border-radius: 12px;
  border: 1px dashed var(--border-color);
  background: var(--preview-bg);
  overflow: hidden;
  padding: 12px;
}
.preview-img {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  display: block;
}
</style>
