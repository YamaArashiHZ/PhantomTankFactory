import { h } from "vue";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { NButton, useMessage, useNotification } from "naive-ui";

/** 启动检查延迟，避免阻塞首屏 */
const STARTUP_CHECK_DELAY_MS = 3000;

export function useUpdater() {
  const message = useMessage();
  const notification = useNotification();

  let installing = false;

  /** 弹出「发现新版本」确认通知，用户确认后下载安装 */
  function promptUpdate(update: Update) {
    const body = (update.body || "").trim();
    notification.info({
      title: `发现新版本 v${update.version}`,
      content: body
        ? body.slice(0, 200) + (body.length > 200 ? "…" : "")
        : "点击「立即更新」下载并安装",
      duration: 0,
      keepAliveOnHover: true,
      onClose: () => {
        void update.close().catch(() => {});
      },
      action: () =>
        h(
          NButton,
          {
            size: "small",
            type: "primary",
            onClick: () => {
              void install(update);
            },
          },
          { default: () => "立即更新" },
        ),
    });
  }

  /** 下载（带进度通知）→ 询问重启 */
  async function install(update: Update) {
    if (installing) return;
    installing = true;

    const progress = notification.info({
      title: `正在下载 v${update.version}`,
      content: "准备下载…",
      duration: 0,
      keepAliveOnHover: true,
      closable: false,
    });

    let total = 0;
    let downloaded = 0;

    try {
      await update.downloadAndInstall((event) => {
        if (event.event === "Started") {
          total = event.data.contentLength ?? 0;
          progress.content = total
            ? `已下载 0%（共 ${(total / 1024 / 1024).toFixed(1)} MB）`
            : "开始下载…";
        } else if (event.event === "Progress") {
          downloaded += event.data.chunkLength;
          if (total > 0) {
            const pct = Math.min(100, Math.round((downloaded / total) * 100));
            progress.content = `已下载 ${pct}%`;
          } else {
            progress.content = `已下载 ${(downloaded / 1024 / 1024).toFixed(1)} MB`;
          }
        } else if (event.event === "Finished") {
          progress.content = "下载完成，正在安装…";
        }
      });

      progress.destroy();
      notification.success({
        title: "更新已就绪",
        content: "安装包已下载完成，重启应用后生效。",
        duration: 0,
        keepAliveOnHover: true,
        action: () =>
          h(
            NButton,
            {
              size: "small",
              type: "primary",
              onClick: () => {
                void relaunch();
              },
            },
            { default: () => "立即重启" },
          ),
      });
    } catch (e) {
      progress.destroy();
      notification.error({
        title: "更新失败",
        content: e instanceof Error ? e.message : String(e),
        duration: 6000,
      });
      void update.close().catch(() => {});
    } finally {
      installing = false;
    }
  }

  /** 静默检查（启动时），有更新才打扰用户 */
  async function checkOnStartup() {
    window.setTimeout(async () => {
      try {
        const update = await check();
        if (update) promptUpdate(update);
      } catch {
        /* 启动静默检查失败不提示 */
      }
    }, STARTUP_CHECK_DELAY_MS);
  }

  /** 手动检查（关于页），给出明确反馈 */
  async function checkManually(): Promise<void> {
    try {
      const update = await check();
      if (update) {
        promptUpdate(update);
      } else {
        message.success("当前已是最新版本");
      }
    } catch (e) {
      notification.error({
        title: "检查更新失败",
        content: e instanceof Error ? e.message : String(e),
        duration: 5000,
      });
    }
  }

  return {
    checkOnStartup,
    checkManually,
  };
}
