<script setup lang="ts">
import { ref, computed, watch, type CSSProperties } from "vue";
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
import { convertFileSrc, invoke } from "@tauri-apps/api/core";
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

/** —— 指针拖拽排序（手机式 App 图标动效 + live 重排 + 占位）—— */
const slotEls = ref<Record<string, HTMLElement>>({});
function setSlotRef(id: string, el: unknown) {
  if (el) slotEls.value[id] = el as HTMLElement;
  else delete slotEls.value[id];
}

const dragId = ref<string | null>(null);
const dragLeft = ref(0);
const dragTop = ref(0);
const dragW = ref(0);
const dragH = ref(0);
let grabX = 0;
let grabY = 0;

const dragFrame = computed(() =>
  innerFrames.value.find((f) => f.id === dragId.value) ?? null,
);

function onHandleDown(e: PointerEvent, id: string) {
  const card = slotEls.value[id];
  if (!card) return;
  const r = card.getBoundingClientRect();
  dragId.value = id;
  dragLeft.value = r.left;
  dragTop.value = r.top;
  dragW.value = r.width;
  dragH.value = r.height;
  grabX = e.clientX - r.left;
  grabY = e.clientY - r.top;
  // 手柄在拖拽中会被占位替换而卸载，故用 window 级监听
  window.addEventListener("pointermove", onHandleMove);
  window.addEventListener("pointerup", onHandleUp);
  window.addEventListener("pointercancel", onHandleUp);
  e.preventDefault();
}

/** 在「非拖拽卡」中按 x 判断插入位置（位于指针左侧的卡数量） */
function insertionIndex(x: number): number {
  let idx = 0;
  for (const f of innerFrames.value) {
    if (f.id === dragId.value) continue;
    const el = slotEls.value[f.id];
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (x > r.left + r.width / 2) idx++;
  }
  return idx;
}

function onHandleMove(e: PointerEvent) {
  if (!dragId.value) return;
  dragLeft.value = e.clientX - grabX;
  dragTop.value = e.clientY - grabY;
  // live 重排：把被拖卡移动到指针所在位置
  const arr = innerFrames.value;
  const cur = arr.findIndex((f) => f.id === dragId.value);
  const to = insertionIndex(e.clientX);
  if (cur >= 0 && to >= 0 && to !== cur) reorderInner(cur, to);
}

function onHandleUp() {
  dragId.value = null;
  window.removeEventListener("pointermove", onHandleMove);
  window.removeEventListener("pointerup", onHandleUp);
  window.removeEventListener("pointercancel", onHandleUp);
}

const ghostStyle = computed<CSSProperties>(() => ({
  position: "fixed",
  left: `${dragLeft.value}px`,
  top: `${dragTop.value}px`,
  width: `${dragW.value}px`,
  height: `${dragH.value}px`,
  zIndex: 999,
  pointerEvents: "none",
  transform: "scale(1.03)",
  boxShadow: "0 14px 36px rgba(0, 0, 0, 0.25)",
}));

/** —— 横向平滑滚动（与全局平滑滚动一致的 lerp 缓动）—— */
const SMOOTH_EASE = 0.18;
const innerRowRef = ref<HTMLElement | null>(null);
let hTarget = 0;
let hRaf = 0;

function clampH(el: HTMLElement, x: number) {
  const max = Math.max(0, el.scrollWidth - el.clientWidth);
  return Math.min(max, Math.max(0, x));
}
function smoothHTick() {
  const el = innerRowRef.value;
  if (!el) {
    hRaf = 0;
    return;
  }
  const cur = el.scrollLeft;
  const diff = hTarget - cur;
  if (Math.abs(diff) < 0.4) {
    el.scrollLeft = hTarget;
    hRaf = 0;
    return;
  }
  el.scrollLeft = cur + diff * SMOOTH_EASE;
  hRaf = requestAnimationFrame(smoothHTick);
}
function onInnerWheel(e: WheelEvent) {
  const el = innerRowRef.value;
  if (!el || el.scrollWidth <= el.clientWidth) return;
  e.preventDefault();
  e.stopPropagation();
  if (!hRaf) hTarget = el.scrollLeft;
  hTarget = clampH(el, hTarget + e.deltaY);
  if (!hRaf) hRaf = requestAnimationFrame(smoothHTick);
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
    <h1 class="page-title fade-up">动图合成（APNG）</h1>
    <p class="page-subtitle fade-up" style="animation-delay: 0.05s">
      选择表图（首帧封面）与若干里图，按每帧时长合成可循环播放的 APNG 动图。
    </p>

    <n-space vertical :size="16" style="width: 100%">
      <!-- 表图 + 里图 选择区 -->
      <n-card size="small" class="fade-up" style="animation-delay: 0.1s">
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

            <div class="inner-row" ref="innerRowRef" @wheel="onInnerWheel">
              <TransitionGroup name="slot" tag="div" class="inner-list">
                <div
                  v-for="(frame, i) in innerFrames"
                  :key="frame.id"
                  class="inner-slot"
                  :ref="(el) => setSlotRef(frame.id, el)"
                >
                <template v-if="dragId === frame.id">
                  <div
                    class="drag-placeholder"
                    :style="{
                      width: dragW ? dragW + 'px' : '220px',
                      height: dragH ? dragH + 'px' : '291px',
                    }"
                  ></div>
                </template>
                <template v-else>
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
                      @pointerdown="onHandleDown($event, frame.id)"
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
                </template>
              </div>
              </TransitionGroup>

              <!-- 添加里图（卡片样式，可拖入图片） -->
              <div class="inner-slot add-slot" @click="addInner()">
                <div
                  ref="addSlotRef"
                  class="add-box"
                  :class="{ 'drag-over': addDragOver }"
                >
                  <n-icon :component="AddOutline" :size="34" class="add-icon" />
                  <n-text depth="3" class="add-label">添加里图</n-text>
                  <n-text depth="3" class="add-hint">点击或拖入图片</n-text>
                </div>
              </div>
            </div>

            <!-- 拖拽幽灵：跟手浮动 -->
            <Teleport to="body">
              <div v-if="dragFrame" class="drag-ghost" :style="ghostStyle">
                <img
                  v-if="dragFrame.path"
                  :src="convertFileSrc(dragFrame.path)"
                  class="ghost-img"
                  alt=""
                />
                <div v-else class="ghost-empty">添加里图</div>
              </div>
            </Teleport>
          </div>
        </div>
      </n-card>

      <!-- 参数 -->
      <n-card title="播放与压缩" size="small" class="fade-up" style="animation-delay: 0.15s">
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
      <n-card title="预览" size="small" class="fade-up" style="animation-delay: 0.2s">
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
      <n-card title="导出" size="small" class="fade-up" style="animation-delay: 0.25s">
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

/* 拖拽占位：被拖卡原位置显示虚线空格 */
.drag-placeholder {
  box-sizing: border-box;
  border: 2px dashed var(--primary-soft);
  border-radius: 14px;
  background: rgba(91, 124, 250, 0.06);
}

/* 拖拽幽灵：跟手浮动 */
.drag-ghost {
  border-radius: 14px;
  overflow: hidden;
  background: var(--preview-bg);
}
.ghost-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ghost-empty {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--n-text-color-3, #999);
  font-size: 14px;
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
  gap: 6px;
  flex-wrap: nowrap;
  white-space: nowrap;
}
.slot-delay {
  margin-top: 2px;
}
.delay-label {
  font-size: 12px;
  flex-shrink: 0;
}
.delay-input {
  width: 84px;
}
.unit {
  color: var(--n-text-color-3, #999);
  font-size: 12px;
  flex-shrink: 0;
}
.hint {
  font-size: 12px;
}

/* 添加里图：仿里图卡片的主按键样式 */
.add-slot {
  cursor: pointer;
  width: 220px;
}
.add-box {
  width: 100%;
  height: 290px;
  box-sizing: border-box;
  border-radius: 14px;
  border: 1px dashed var(--border-color);
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--n-text-color-3, #999);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.add-box:hover,
.add-box.drag-over {
  border-color: var(--primary-soft);
}
.add-icon {
  color: var(--primary-soft);
}
.add-label {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}
.add-hint {
  text-align: center;
  font-size: 12px;
  opacity: 0.8;
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

/* —— 项目风格动效：淡入上移（与全局页面过渡同款缓动）—— */
@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.fade-up {
  animation: fade-up 0.35s cubic-bezier(0.4, 0, 0.2, 1) both;
}

/* —— 里图卡列表 TransitionGroup：新增淡入 / 重排滑动 / 移除淡出 —— */
.inner-list {
  position: relative;
  display: flex;
  gap: 12px;
}
.slot-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.slot-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.slot-leave-active {
  position: absolute;
  transition: opacity 0.2s ease;
}
.slot-leave-to {
  opacity: 0;
}
.slot-move {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
