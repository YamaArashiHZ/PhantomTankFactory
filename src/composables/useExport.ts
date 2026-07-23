import { computed, h, ref, type Ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { NButton, useMessage, useNotification } from "naive-ui";
import type { ProcessResult } from "../types";
import { useAppConfig } from "./useAppConfig";

/** 导出流程：合成幻影坦克并以底部横幅通知结果。 */
export function useExport(
  surfacePath: Ref<string | null>,
  innerPath: Ref<string | null>,
) {
  const message = useMessage();
  const notification = useNotification();
  const { brightnessEnhancement, brightnessReduction, exportDirectory } =
    useAppConfig();

  const processing = ref(false);

  const canProcess = computed(
    () => !!surfacePath.value && !!innerPath.value && !processing.value,
  );

  function showExportDoneBanner(outputPath: string) {
    const fileName =
      outputPath.replace(/\\/g, "/").split("/").pop() || outputPath;
    notification.success({
      title: "合成完成",
      content: fileName,
      meta: outputPath,
      duration: 6500,
      keepAliveOnHover: true,
      action: () =>
        h(
          NButton,
          {
            size: "small",
            secondary: true,
            type: "primary",
            onClick: () => {
              void revealItemInDir(outputPath).catch((e) => {
                message.error(String(e));
              });
            },
          },
          { default: () => "在文件夹中显示" },
        ),
    });
  }

  async function process() {
    if (!surfacePath.value || !innerPath.value) {
      message.warning("请先选择表图和里图");
      return;
    }
    processing.value = true;
    try {
      const result = await invoke<ProcessResult>("process_phantom_tank", {
        surfacePath: surfacePath.value,
        innerPath: innerPath.value,
        brightnessEnhancement: brightnessEnhancement.value,
        brightnessReduction: brightnessReduction.value,
        exportDirectory: exportDirectory.value || "",
      });
      showExportDoneBanner(result.outputPath);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      notification.error({
        title: "合成失败",
        content: msg || "未知错误",
        duration: 5000,
      });
    } finally {
      processing.value = false;
    }
  }

  return {
    processing,
    canProcess,
    process,
  };
}
