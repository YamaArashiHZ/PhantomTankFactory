<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  NCard,
  NEmpty,
  NSpin,
  NText,
  NSelect,
  NSpace,
  NCheckbox,
} from "naive-ui";
import type { PreviewQuality } from "../types";

/** 与选图区相同：横/竖比例上限 16:9 → 宽高比 9:16 ~ 16:9 */
const ASPECT_MAX = 16 / 9;
const ASPECT_MIN = 9 / 16;
const DEFAULT_ASPECT = 16 / 9;

const props = defineProps<{
  surfacePreview: string | null;
  innerPreview: string | null;
  loading: boolean;
  ready: boolean;
  error: string | null;
  quality: PreviewQuality;
  enabled: boolean;
}>();

const emit = defineEmits<{
  "update:quality": [value: PreviewQuality];
  "update:enabled": [value: boolean];
}>();

const qualityOptions = [
  { label: "低", value: "low" as const },
  { label: "中", value: "medium" as const },
  { label: "高", value: "high" as const },
  { label: "原图", value: "original" as const },
];

const naturalW = ref(0);
const naturalH = ref(0);

const boxAspect = computed(() => {
  if (naturalW.value <= 0 || naturalH.value <= 0) return DEFAULT_ASPECT;
  const raw = naturalW.value / naturalH.value;
  return Math.min(ASPECT_MAX, Math.max(ASPECT_MIN, raw));
});

const paneBoxStyle = computed(() => ({
  width: "100%",
  aspectRatio: String(boxAspect.value),
  maxHeight: "78vh",
}));

watch(
  () => [props.surfacePreview, props.innerPreview, props.ready] as const,
  () => {
    if (!props.ready || !props.surfacePreview) {
      naturalW.value = 0;
      naturalH.value = 0;
    }
  },
);

function onImgLoad(e: Event) {
  const img = e.target as HTMLImageElement;
  if (img.naturalWidth > 0 && img.naturalHeight > 0) {
    naturalW.value = img.naturalWidth;
    naturalH.value = img.naturalHeight;
  }
}
</script>

<template>
  <n-card size="small" class="effect-card" :class="{ 'is-off': !enabled }">
    <template #header>
      <div class="title-row">
        <span class="title-text">效果预览</span>
        <n-checkbox
          :checked="enabled"
          @update:checked="(v) => emit('update:enabled', !!v)"
        >
          启用
        </n-checkbox>
      </div>
    </template>

    <template #header-extra>
      <n-space v-show="enabled" align="center" :size="10" class="header-extra">
        <n-text depth="3" style="font-size: 12px">清晰度</n-text>
        <n-select
          :value="quality"
          :options="qualityOptions"
          size="tiny"
          style="width: 88px"
          :disabled="!enabled"
          @update:value="(v) => emit('update:quality', v as PreviewQuality)"
        />
        <n-text v-if="loading" depth="3" style="font-size: 12px">更新中…</n-text>
        <n-text v-else-if="ready" depth="3" style="font-size: 12px">随亮度实时更新</n-text>
      </n-space>
    </template>

    <div class="body-collapse" :class="{ open: enabled }">
      <div class="body-inner">
        <n-text depth="3" class="quality-tip">
          提示：清晰度仅影响预览，不影响最终导出；档位过高时预览生成可能较慢。
        </n-text>

        <n-spin :show="loading && ready && enabled">
          <div v-if="!ready" class="empty-wrap">
            <n-empty description="请先选择表图与里图" size="small" />
          </div>
          <div v-else-if="error" class="empty-wrap">
            <n-empty :description="error" size="small" />
          </div>
          <div v-else class="preview-grid">
            <div class="pane">
              <div class="pane-label">表图效果（白底 / 缩略图）</div>
              <div class="pane-box surface" :style="paneBoxStyle">
                <img
                  v-if="surfacePreview"
                  :key="surfacePreview.slice(0, 64)"
                  :src="surfacePreview"
                  alt="表图效果"
                  class="pane-img"
                  draggable="false"
                  @load="onImgLoad"
                />
              </div>
            </div>
            <div class="pane">
              <div class="pane-label">里图效果（黑底 / 点开大图）</div>
              <div class="pane-box inner" :style="paneBoxStyle">
                <img
                  v-if="innerPreview"
                  :key="innerPreview.slice(0, 64)"
                  :src="innerPreview"
                  alt="里图效果"
                  class="pane-img"
                  draggable="false"
                />
              </div>
            </div>
          </div>
        </n-spin>
      </div>
    </div>
  </n-card>
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-text {
  font-weight: 600;
}

.header-extra {
  transition: opacity 0.28s ease, transform 0.28s ease;
}

.effect-card.is-off .header-extra {
  opacity: 0;
  pointer-events: none;
  transform: translateX(6px);
}

/* 网格行高折叠：平滑展开/收起 */
.body-collapse {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  transition:
    grid-template-rows 0.35s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.28s ease,
    margin 0.35s ease;
  margin-top: 0;
}

.body-collapse.open {
  grid-template-rows: 1fr;
  opacity: 1;
}

.body-inner {
  overflow: hidden;
  min-height: 0;
}

.quality-tip {
  display: block;
  font-size: 12px;
  margin: 0 0 12px;
  line-height: 1.5;
}

.empty-wrap {
  min-height: 160px;
  display: grid;
  place-items: center;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
  align-items: start;
}

.pane {
  min-width: 0;
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pane-label {
  font-size: 12px;
  opacity: 0.7;
}

.pane-box {
  position: relative;
  margin: 0;
  min-height: 160px;
  height: auto;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-sizing: border-box;
  transition: aspect-ratio 0.2s ease;
}

.pane-box.surface {
  background: #ffffff;
}

.pane-box.inner {
  background: #0a0a0a;
}

.pane-img {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
  pointer-events: none;
  user-select: none;
}

@media (max-width: 720px) {
  .preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
