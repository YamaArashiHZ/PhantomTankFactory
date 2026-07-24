<script setup lang="ts">
import { ref, watch } from "vue";
import { NCard, NFormItem, NSlider, NInputNumber, NSpace, NText, NButton, NSelect } from "naive-ui";
import { DEFAULT_MODE_PARAMS, DEFAULT_CONFIG, type ColorMode } from "../types";

const props = defineProps<{
  enhancement: number;
  reduction: number;
  contrast: number;
  saturation: number;
  colorMode: ColorMode;
}>();

const emit = defineEmits<{
  "update:enhancement": [value: number];
  "update:reduction": [value: number];
  "update:contrast": [value: number];
  "update:saturation": [value: number];
  "update:colorMode": [value: ColorMode];
}>();

const colorModeOptions = [
  { label: "黑白", value: "grayscale" },
  { label: "彩色（实验性）", value: "color" },
];

function smoothRef(forProp: () => number) {
  const r = ref(forProp());
  let animFrame = 0;
  watch(forProp, (to) => {
    cancelAnimationFrame(animFrame);
    const from = r.value;
    if (from === to) return;
    const start = performance.now();
    const dur = 280;
    function tick() {
      const p = Math.min((performance.now() - start) / dur, 1);
      const e = 1 - (1 - p) ** 3;
      r.value = Math.round(from + (to - from) * e);
      if (p < 1) {
        animFrame = requestAnimationFrame(tick);
      }
    }
    tick();
  });
  return r;
}

const smoothEnhancement = smoothRef(() => props.enhancement);
const smoothReduction = smoothRef(() => props.reduction);
const smoothContrast = smoothRef(() => props.contrast);
const smoothSaturation = smoothRef(() => props.saturation);

function resetDefaults() {
  emit("update:enhancement", DEFAULT_MODE_PARAMS.brightnessEnhancement);
  emit("update:reduction", DEFAULT_MODE_PARAMS.brightnessReduction);
  emit("update:contrast", DEFAULT_MODE_PARAMS.contrast);
  emit("update:saturation", DEFAULT_MODE_PARAMS.saturation);
  emit("update:colorMode", DEFAULT_CONFIG.colorMode);
}
</script>

<template>
  <n-card size="small">
    <template #header>
      <div class="card-header-row">
        <span>图像参数</span>
        <n-select
          :value="colorMode"
          :options="colorModeOptions"
          size="small"
          style="width: 160px"
          @update:value="(v) => emit('update:colorMode', v as ColorMode)"
        />
        <n-text v-if="colorMode === 'color'" depth="3" style="font-size: 12px">
          合成彩色幻影坦克时尽可能使用差分图，否则生成效果较差甚至无效
        </n-text>
      </div>
    </template>
    <template #header-extra>
      <n-button size="tiny" quaternary @click="resetDefaults">恢复默认</n-button>
    </template>
    <n-space vertical :size="18">
      <div>
        <n-form-item label="表图亮度增强 (0 ~ 100)" :show-feedback="false">
          <div class="slider-row">
            <n-slider
              class="slider"
              :value="smoothEnhancement"
              :min="0"
              :max="100"
              :step="1"
              @update:value="(v) => emit('update:enhancement', Number(v))"
            />
            <n-input-number
              :value="smoothEnhancement"
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
              :value="smoothReduction"
              :min="-100"
              :max="0"
              :step="1"
              @update:value="(v) => emit('update:reduction', Number(v))"
            />
            <n-input-number
              :value="smoothReduction"
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
              :value="smoothContrast"
              :min="-100"
              :max="100"
              :step="1"
              @update:value="(v) => emit('update:contrast', Number(v))"
            />
            <n-input-number
              :value="smoothContrast"
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

      <Transition name="fade-slide">
        <div v-if="colorMode === 'color'">
          <n-form-item label="饱和度 (-100 ~ 100)" :show-feedback="false">
          <div class="slider-row">
            <n-slider
              class="slider"
              :value="smoothSaturation"
              :min="-100"
              :max="100"
              :step="1"
              @update:value="(v) => emit('update:saturation', Number(v))"
            />
            <n-input-number
              :value="smoothSaturation"
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
      </Transition>
    </n-space>
  </n-card>
</template>

<style scoped>
.card-header-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

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

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  margin-bottom: 0;
}

.fade-slide-enter-to,
.fade-slide-leave-from {
  opacity: 1;
  max-height: 120px;
}
</style>
