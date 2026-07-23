<script setup lang="ts">
import { computed, watch } from "vue";
import { NCard, NButton, NText, NIcon, NEmpty } from "naive-ui";
import { ImageOutline, CloseCircleOutline } from "@vicons/ionicons5";
import { convertFileSrc } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

const props = defineProps<{
  title: string;
  hint: string;
  path: string | null;
  /** 父级统一宽高比（两卡同步），未传则用默认 16:9 */
  boxAspect?: number;
}>();

const emit = defineEmits<{
  "update:path": [value: string | null];
  /** 图片自然尺寸变化；清除或无效时为 null */
  "natural-size": [size: { width: number; height: number } | null];
}>();

const DEFAULT_ASPECT = 16 / 9;

const previewUrl = computed(() => (props.path ? convertFileSrc(props.path) : ""));
const fileName = computed(() => {
  if (!props.path) return "";
  const parts = props.path.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || props.path;
});

const resolvedAspect = computed(() =>
  props.boxAspect && props.boxAspect > 0 ? props.boxAspect : DEFAULT_ASPECT,
);

const previewBoxStyle = computed(() => ({
  // 始终铺满卡片宽度，高度由统一比例决定；图片 contain 尽量填满框
  width: "100%",
  aspectRatio: String(resolvedAspect.value),
  maxHeight: "78vh",
}));

watch(
  () => props.path,
  (p) => {
    if (!p) emit("natural-size", null);
  },
);

function onImgLoad(e: Event) {
  const img = e.target as HTMLImageElement;
  if (img.naturalWidth > 0 && img.naturalHeight > 0) {
    emit("natural-size", { width: img.naturalWidth, height: img.naturalHeight });
  } else {
    emit("natural-size", null);
  }
}

async function pickImage() {
  const selected = await open({
    multiple: false,
    directory: false,
    filters: [
      {
        name: "图片",
        extensions: ["png", "jpg", "jpeg", "bmp", "webp", "gif"],
      },
    ],
  });
  if (typeof selected === "string") {
    emit("update:path", selected);
  }
}

function clear() {
  emit("update:path", null);
  emit("natural-size", null);
}
</script>

<template>
  <n-card
    class="picker-card"
    :title="title"
    size="small"
    :bordered="true"
    :content-style="{ overflow: 'visible', paddingBottom: '12px' }"
  >
    <template #header-extra>
      <n-button v-if="path" quaternary size="tiny" @click.stop="clear">
        <template #icon>
          <n-icon :component="CloseCircleOutline" />
        </template>
        清除
      </n-button>
    </template>

    <div
      class="preview-box"
      :class="{ empty: !path }"
      :style="previewBoxStyle"
      @click="pickImage"
      role="button"
      tabindex="0"
      @keydown.enter="pickImage"
    >
      <img
        v-if="path"
        :key="path"
        :src="previewUrl"
        :alt="title"
        class="preview-img"
        draggable="false"
        @load="onImgLoad"
      />
      <div v-else class="placeholder">
        <n-empty :description="hint" size="small">
          <template #icon>
            <n-icon :component="ImageOutline" :size="28" />
          </template>
        </n-empty>
      </div>
    </div>

    <div class="footer">
      <n-text depth="3" class="filename" :title="path || ''">
        {{ path ? fileName : "未选择" }}
      </n-text>
      <n-button size="small" secondary type="primary" @click.stop="pickImage">
        选择图片
      </n-button>
    </div>
  </n-card>
</template>

<style scoped>
.picker-card {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.picker-card :deep(.n-card-header) {
  overflow: hidden;
}

.picker-card :deep(.n-card-header__main) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-card :deep(.n-card__content) {
  overflow: hidden !important;
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}

.preview-box {
  position: relative;
  margin: 0;
  min-height: 160px;
  height: auto;
  padding: 8px;
  border-radius: 12px;
  border: 1px dashed var(--border-color);
  background: var(--preview-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, aspect-ratio 0.2s ease;
  box-sizing: border-box;
}

.preview-box:hover {
  border-color: var(--primary-soft);
}

.preview-img {
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

.placeholder {
  pointer-events: none;
  padding: 12px;
}

.footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-shrink: 0;
  min-width: 0;
  width: 100%;
}

.footer :deep(.n-button) {
  flex-shrink: 0;
}

.filename {
  flex: 1 1 0;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
</style>
