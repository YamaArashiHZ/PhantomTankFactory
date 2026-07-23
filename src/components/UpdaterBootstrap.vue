<script setup lang="ts">
import { onMounted } from "vue";
import { useUpdater } from "../composables/useUpdater";

const { checkOnStartup } = useUpdater();

onMounted(() => {
  checkOnStartup();
});
</script>

<template>
  <!-- 无渲染：仅启动时触发更新检查（须在通知 Provider 内） -->
</template>
