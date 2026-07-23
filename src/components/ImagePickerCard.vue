<script setup lang="ts">
import { computed } from "vue";
import { NCard, NButton, NText, NIcon, NEmpty } from "naive-ui";
import { ImageOutline, CloseCircleOutline } from "@vicons/ionicons5";
import { convertFileSrc } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

const props = defineProps<{
  title: string;
  hint: string;
  path: string | null;
}>();

const emit = defineEmits<{
  "update:path": [value: string | null];
}>();

const previewUrl = computed(() => (props.path ? convertFileSrc(props.path) : ""));
const fileName = computed(() => {
  if (!props.path) return "";
  const parts = props.path.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || props.path;
});

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
}
</script>

<template>
  <n-card class="picker-card" :title="title" size="small" :bordered="true">
    <template #header-extra>
      <n-button v-if="path" quaternary size="tiny" @click="clear">
        <template #icon>
          <n-icon :component="CloseCircleOutline" />
        </template>
        清除
      </n-button>
    </template>

    <div class="preview-box" @click="pickImage" role="button" tabindex="0" @keydown.enter="pickImage">
      <img v-if="path" :src="previewUrl" :alt="title" class="preview-img" />
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
      <n-button size="small" secondary type="primary" @click="pickImage">选择图片</n-button>
    </div>
  </n-card>
</template>

<style scoped>
.picker-card {
  height: 100%;
}

.preview-box {
  height: 180px;
  border-radius: 12px;
  border: 1px dashed var(--border-color);
  background: var(--preview-bg);
  display: grid;
  place-items: center;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.preview-box:hover {
  border-color: var(--primary-soft);
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
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
}

.filename {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
</style>
