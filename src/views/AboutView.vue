<script setup lang="ts">
import { NCard, NSpace, NText, NTag, NIcon, useMessage } from "naive-ui";
import { LogoGithub, LinkOutline } from "@vicons/ionicons5";
import { openUrl } from "@tauri-apps/plugin-opener";

const message = useMessage();

const APP_NAME = "PhantomTank Factory";
const APP_VERSION = "0.1.0";
const APP_AUTHOR = "YamaArashi";

const links = [
  {
    key: "github",
    label: "GitHub",
    desc: "项目仓库",
    url: "https://github.com/YamaArashiHZ/PhantomTankFactory",
    icon: LogoGithub,
  },
  {
    key: "bilibili",
    label: "Bilibili",
    desc: "作者空间",
    url: "https://space.bilibili.com/319279623",
    icon: LinkOutline,
  },
] as const;

async function openLink(url: string) {
  try {
    await openUrl(url);
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e));
  }
}
</script>

<template>
  <div class="about">
    <h1 class="page-title">关于</h1>
    <p class="page-subtitle">{{ APP_NAME }} · 幻影坦克合成工具</p>

    <n-space vertical :size="16" style="width: 100%">
      <n-card size="small" title="应用信息">
        <div class="info-grid">
          <div class="info-item">
            <n-text depth="3" class="info-label">名称</n-text>
            <n-text class="info-value">{{ APP_NAME }}</n-text>
          </div>
          <div class="info-item">
            <n-text depth="3" class="info-label">版本</n-text>
            <div class="info-value">
              <n-tag size="small" type="info" :bordered="false">{{ APP_VERSION }}</n-tag>
            </div>
          </div>
          <div class="info-item">
            <n-text depth="3" class="info-label">作者</n-text>
            <n-text class="info-value">{{ APP_AUTHOR }}</n-text>
          </div>
        </div>

        <div class="links-block">
          <n-text depth="3" class="info-label">相关链接</n-text>
          <div class="links-grid">
            <button
              v-for="item in links"
              :key="item.key"
              type="button"
              class="link-card"
              :title="item.url"
              @click="openLink(item.url)"
            >
              <span class="link-icon">
                <n-icon :component="item.icon" :size="20" />
              </span>
              <span class="link-meta">
                <span class="link-title">{{ item.label }}</span>
                <span class="link-desc">{{ item.desc }}</span>
                <span class="link-url">{{ item.url }}</span>
              </span>
              <span class="link-action">打开</span>
            </button>
          </div>
        </div>
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
.about {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--preview-bg);
  border: 1px solid var(--border-color);
}

.info-label {
  font-size: 12px;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  word-break: break-all;
}

.links-block {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.links-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.link-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--preview-bg);
  cursor: pointer;
  text-align: left;
  color: inherit;
  font: inherit;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}

.link-card:hover {
  border-color: var(--primary-soft);
  transform: translateY(-1px);
}

.link-card:active {
  transform: translateY(0);
}

.link-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: rgba(91, 124, 250, 0.12);
  color: var(--primary-soft);
}

.link-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.link-title {
  font-size: 14px;
  font-weight: 600;
}

.link-desc {
  font-size: 12px;
  opacity: 0.65;
}

.link-url {
  font-size: 11px;
  opacity: 0.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-action {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-soft);
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(91, 124, 250, 0.12);
}

.tips {
  margin: 0;
  padding-left: 18px;
  line-height: 1.8;
  opacity: 0.85;
  font-size: 13px;
}

@media (max-width: 720px) {
  .info-grid,
  .links-grid {
    grid-template-columns: 1fr;
  }
}
</style>
