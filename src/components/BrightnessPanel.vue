<script setup lang="ts">
import { NCard, NFormItem, NSlider, NInputNumber, NSpace, NText, NButton } from "naive-ui";
import { DEFAULT_CONFIG } from "../types";

defineProps<{
  enhancement: number;
  reduction: number;
  contrast: number;
  saturation: number;
}>();

const emit = defineEmits<{
  "update:enhancement": [value: number];
  "update:reduction": [value: number];
  "update:contrast": [value: number];
  "update:saturation": [value: number];
}>();

function resetDefaults() {
  emit("update:enhancement", DEFAULT_CONFIG.brightnessEnhancement);
  emit("update:reduction", DEFAULT_CONFIG.brightnessReduction);
  emit("update:contrast", DEFAULT_CONFIG.contrast);
  emit("update:saturation", DEFAULT_CONFIG.saturation);
}
</script>

<template>
  <n-card title="图像参数" size="small">
    <template #header-extra>
      <n-button size="tiny" quaternary @click="resetDefaults">恢复默认</n-button>
    </template>
    <n-space vertical :size="18">
      <div>
        <n-form-item label="表图亮度增强 (0 ~ 100)" :show-feedback="false">
          <div class="slider-row">
            <n-slider
              class="slider"
              :value="enhancement"
              :min="0"
              :max="100"
              :step="1"
              @update:value="(v) => emit('update:enhancement', Number(v))"
            />
            <n-input-number
              :value="enhancement"
              :min="0"
              :max="100"
              :step="1"
              size="small"
              class="num-input"
              @update:value="(v) => emit('update:enhancement', Number(v ?? 0))"
            />
          </div>
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">数值越大，缩略图中表图越亮、越明显。</n-text>
      </div>

      <div>
        <n-form-item label="里图亮度削减 (-100 ~ 0)" :show-feedback="false">
          <div class="slider-row">
            <n-slider
              class="slider"
              :value="reduction"
              :min="-100"
              :max="0"
              :step="1"
              @update:value="(v) => emit('update:reduction', Number(v))"
            />
            <n-input-number
              :value="reduction"
              :min="-100"
              :max="0"
              :step="1"
              size="small"
              class="num-input"
              @update:value="(v) => emit('update:reduction', Number(v ?? 0))"
            />
          </div>
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">越接近 -100，点开大图后里图越暗（对比更强）。</n-text>
      </div>

      <div>
        <n-form-item label="对比度 (-100 ~ 100)" :show-feedback="false">
          <div class="slider-row">
            <n-slider
              class="slider"
              :value="contrast"
              :min="-100"
              :max="100"
              :step="1"
              @update:value="(v) => emit('update:contrast', Number(v))"
            />
            <n-input-number
              :value="contrast"
              :min="-100"
              :max="100"
              :step="1"
              size="small"
              class="num-input"
              @update:value="(v) => emit('update:contrast', Number(v ?? 0))"
            />
          </div>
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">增强图像明暗差异。0 为不变，负值降低对比度。</n-text>
      </div>

      <div>
        <n-form-item label="饱和度 (-100 ~ 100)" :show-feedback="false">
          <div class="slider-row">
            <n-slider
              class="slider"
              :value="saturation"
              :min="-100"
              :max="100"
              :step="1"
              @update:value="(v) => emit('update:saturation', Number(v))"
            />
            <n-input-number
              :value="saturation"
              :min="-100"
              :max="100"
              :step="1"
              size="small"
              class="num-input"
              @update:value="(v) => emit('update:saturation', Number(v ?? 0))"
            />
          </div>
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">调整色彩鲜艳程度。0 为不变，-100 转为灰度。</n-text>
      </div>
    </n-space>
  </n-card>
</template>

<style scoped>
.slider-row {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.slider {
  flex: 1 1 auto;
  /* 原 160px，加长一倍 */
  min-width: 320px;
  width: 100%;
}

.num-input {
  flex: 0 0 100px;
  width: 100px;
}
</style>
