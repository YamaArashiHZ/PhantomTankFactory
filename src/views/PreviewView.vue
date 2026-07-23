<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  NButton,
  NCard,
  NEmpty,
  NIcon,
  NSpace,
  NText,
  useMessage,
} from "naive-ui";
import { CloseCircleOutline, FolderOpenOutline } from "@vicons/ionicons5";
import { convertFileSrc } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

/** 与选图区相同：宽高比 9:16 ~ 16:9 */
const ASPECT_MAX = 16 / 9;
const ASPECT_MIN = 9 / 16;
const DEFAULT_ASPECT = 16 / 9;

const message = useMessage();
const imagePath = ref<string | null>(null);
const naturalW = ref(0);
const naturalH = ref(0);

const previewUrl = computed(() =>
  imagePath.value ? convertFileSrc(imagePath.value) : "",
);

const fileName = computed(() => {
  if (!imagePath.value) return "";
  const parts = imagePath.value.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || imagePath.value;
});

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

watch(imagePath, () => {
  naturalW.value = 0;
  naturalH.value = 0;
});

function onImgLoad(e: Event) {
  const img = e.target as HTMLImageElement;
  if (img.naturalWidth > 0 && img.naturalHeight > 0) {
    naturalW.value = img.naturalWidth;
    naturalH.value = img.naturalHeight;
  }
}

async function pickImage() {
  const selected = await open({
    multiple: false,
    directory: false,
    filters: [
      {
        name: "幻影坦克 / 图片",
        extensions: ["png", "webp", "jpg", "jpeg", "bmp", "gif"],
      },
    ],
  });
  if (typeof selected === "string") {
    imagePath.value = selected;
  }
}

function clear() {
  imagePath.value = null;
}

function onImgError() {
  message.error("无法加载图片，请确认文件有效");
  imagePath.value = null;
}
</script>

<template>
  <div class="preview-page">
    <h1 class="page-title">效果查看</h1>
    <p class="page-subtitle">
      选择已生成的幻影坦克 PNG，在白底 / 黑底下查看表图与里图效果。
    </p>

    <n-space vertical :size="16" style="width: 100%">
      <n-card title="选择图片" size="small">
        <div class="pick-row">
          <n-text depth="3" class="path-text" :title="imagePath || ''">
            {{ imagePath ? fileName : "未选择文件" }}
          </n-text>
          <n-space :size="8">
            <n-button v-if="imagePath" quaternary size="small" @click="clear">
              <template #icon>
                <n-icon :component="CloseCircleOutline" />
              </template>
              清除
            </n-button>
            <n-button type="primary" secondary @click="pickImage">
              <template #icon>
                <n-icon :component="FolderOpenOutline" />
              </template>
              选择图片
            </n-button>
          </n-space>
        </div>
      </n-card>

      <n-card title="效果预览" size="small">
        <div v-if="!imagePath" class="empty-wrap">
          <n-empty description="请选择幻影坦克" size="small" />
        </div>
        <div v-else class="preview-grid">
          <div class="pane">
            <div class="pane-label">表图效果（白底 / 缩略图）</div>
            <div class="pane-box surface" :style="paneBoxStyle">
              <img
                :key="previewUrl + '-s'"
                :src="previewUrl"
                alt="表图效果"
                class="pane-img"
                draggable="false"
                @load="onImgLoad"
                @error="onImgError"
              />
            </div>
          </div>
          <div class="pane">
            <div class="pane-label">里图效果（黑底 / 点开大图）</div>
            <div class="pane-box inner" :style="paneBoxStyle">
              <img
                :key="previewUrl + '-i'"
                :src="previewUrl"
                alt="里图效果"
                class="pane-img"
                draggable="false"
              />
            </div>
          </div>
        </div>
      </n-card>
    </n-space>
  </div>
</template>

<style scoped>
.preview-page {
  width: 100%;
  box-sizing: border-box;
}

.pick-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.path-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
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
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pane-label {
  font-size: 12px;
  opacity: 0.7;
}

.pane-box {
  min-height: 160px;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-sizing: border-box;
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
