<script setup lang="ts">
import { NCard, NSpace, NText, NTag } from "naive-ui";
</script>

<template>
  <div class="about">
    <h1 class="page-title">关于</h1>
    <p class="page-subtitle">PhantomTank Factory · 幻影坦克合成工具</p>

    <n-space vertical :size="16" style="max-width: 720px">
      <n-card size="small" title="应用信息">
        <n-space vertical :size="8">
          <div class="row">
            <n-text depth="3">名称</n-text>
            <n-text>PhantomTank Factory</n-text>
          </div>
          <div class="row">
            <n-text depth="3">版本</n-text>
            <n-tag size="small" type="info" :bordered="false">0.1.0</n-tag>
          </div>
          <div class="row">
            <n-text depth="3">作者</n-text>
            <n-text>YamaArashi</n-text>
          </div>
        </n-space>
      </n-card>

      <n-card size="small" title="使用提示">
        <ul class="tips">
          <li>表图、里图建议主体清晰；尺寸差异过大会自动缩放并透明填充。</li>
          <li>默认亮度（表 +50 / 里 -50）适合多数场景，可按预览平台微调。</li>
          <li>导出为 PNG 以保留透明度通道，请勿转存为会丢 Alpha 的格式。</li>
          <li>效果因聊天软件 / 图床的缩略图算法而异，请以目标平台实测为准。</li>
        </ul>
      </n-card>
    </n-space>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.tips {
  margin: 0;
  padding-left: 18px;
  line-height: 1.8;
  opacity: 0.85;
  font-size: 13px;
}
</style>
