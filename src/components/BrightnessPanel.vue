<script setup lang="ts">
import { NCard, NFormItem, NSlider, NInputNumber, NSpace, NText } from "naive-ui";

defineProps<{
  enhancement: number;
  reduction: number;
}>();

const emit = defineEmits<{
  "update:enhancement": [value: number];
  "update:reduction": [value: number];
}>();
</script>

<template>
  <n-card title="亮度参数" size="small">
    <n-space vertical :size="18">
      <div>
        <n-form-item label="表图亮度增强 (0 ~ 100)" :show-feedback="false">
          <n-space align="center" style="width: 100%">
            <n-slider
              :value="enhancement"
              :min="0"
              :max="100"
              :step="1"
              style="flex: 1; min-width: 160px"
              @update:value="(v) => emit('update:enhancement', Number(v))"
            />
            <n-input-number
              :value="enhancement"
              :min="0"
              :max="100"
              :step="1"
              size="small"
              style="width: 100px"
              @update:value="(v) => emit('update:enhancement', Number(v ?? 0))"
            />
          </n-space>
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">数值越大，缩略图中表图越亮、越明显。</n-text>
      </div>

      <div>
        <n-form-item label="里图亮度削减 (-100 ~ 0)" :show-feedback="false">
          <n-space align="center" style="width: 100%">
            <n-slider
              :value="reduction"
              :min="-100"
              :max="0"
              :step="1"
              style="flex: 1; min-width: 160px"
              @update:value="(v) => emit('update:reduction', Number(v))"
            />
            <n-input-number
              :value="reduction"
              :min="-100"
              :max="0"
              :step="1"
              size="small"
              style="width: 100px"
              @update:value="(v) => emit('update:reduction', Number(v ?? 0))"
            />
          </n-space>
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">越接近 -100，点开大图后里图越暗（对比更强）。</n-text>
      </div>
    </n-space>
  </n-card>
</template>
