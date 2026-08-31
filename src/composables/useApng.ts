import { computed, h, onBeforeUnmount, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { NButton, useMessage, useNotification } from "naive-ui";
import type {
  ApngInnerFrame,
  ApngLoop,
  ApngPreviewResult,
  ApngResult,
} from "../types";
import { useAppConfig } from "./useAppConfig";

export const DEFAULT_DELAY_MS = 1000;
/** 预览时最长边限制 */
const PREVIEW_EDGE = 480;
/** 预览防抖 */
const PREVIEW_DEBOUNCE_MS = 280;

export function useApng() {
  const message = useMessage();
  const notification = useNotification();
  const { exportDirectory } = useAppConfig();

  const surfacePath = ref<string | null>(null);
  const surfaceDelayMs = ref(DEFAULT_DELAY_MS);

  const innerFrames = ref<ApngInnerFrame[]>([
    { path: null, delayMs: DEFAULT_DELAY_MS },
  ]);

  const loop = ref<ApngLoop>("infinite");
  const times = ref(3);
  const compression = ref(6);
  const grayscale = ref(false);
  /** 成品大小上限（KB）；null = 不限制 */
  const maxSizeKb = ref<number | null>(null);

  const processing = ref(false);
  const previewing = ref(false);
  const previewUrl = ref<string | null>(null);
  const previewError = ref<string | null>(null);

  const filledInners = computed(
    () => innerFrames.value.filter((f) => f.path).length,
  );
  const canProcess = computed(
    () => !!surfacePath.value && filledInners.value >= 1,
  );

  function addInner() {
    innerFrames.value.push({ path: null, delayMs: DEFAULT_DELAY_MS });
  }
  function removeInner(i: number) {
    innerFrames.value.splice(i, 1);
  }
  function setInnerPath(i: number, path: string | null) {
    innerFrames.value[i]!.path = path;
  }
  function setInnerDelay(i: number, ms: number) {
    innerFrames.value[i]!.delayMs = ms;
  }
  function setAllDelays(ms: number) {
    surfaceDelayMs.value = ms;
    for (const f of innerFrames.value) f.delayMs = ms;
  }
  function reorderInner(from: number, to: number) {
    const arr = innerFrames.value;
    if (
      from < 0 ||
      from >= arr.length ||
      to < 0 ||
      to >= arr.length ||
      from === to
    ) {
      return;
    }
    const [moved] = arr.splice(from, 1);
    arr.splice(to, 0, moved!);
  }

  const loopPlays = computed(() => {
    if (loop.value === "infinite") return 0;
    if (loop.value === "once") return 1;
    return Math.max(1, Math.floor(times.value));
  });

  function basePayload() {
    const innerPaths = innerFrames.value
      .map((f) => f.path)
      .filter((p): p is string => !!p);
    const innerDelaysMs = innerFrames.value
      .filter((f) => f.path)
      .map((f) => f.delayMs);
    return {
      surfacePath: surfacePath.value as string,
      surfaceDelayMs: surfaceDelayMs.value,
      innerPaths,
      innerDelaysMs,
      loopPlays: loopPlays.value,
      compression: compression.value,
      grayscale: grayscale.value,
    };
  }

  let timer: ReturnType<typeof setTimeout> | null = null;
  async function runPreview() {
    if (!canProcess.value) {
      previewUrl.value = null;
      previewError.value = null;
      return;
    }
    previewing.value = true;
    previewError.value = null;
    try {
      const res = await invoke<ApngPreviewResult>("preview_apng", {
        ...basePayload(),
        maxEdge: PREVIEW_EDGE,
      });
      previewUrl.value = res.dataUrl;
    } catch (e) {
      previewError.value = e instanceof Error ? e.message : String(e);
      previewUrl.value = null;
    } finally {
      previewing.value = false;
    }
  }
  function schedulePreview() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void runPreview(), PREVIEW_DEBOUNCE_MS);
  }

  function showDone(result: ApngResult) {
    const file =
      result.outputPath.replace(/\\/g, "/").split("/").pop() || result.outputPath;
    notification.success({
      title: "动图导出完成",
      content: `${file} (~${result.sizeKb} KB)`,
      meta: result.warning || undefined,
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
              void revealItemInDir(result.outputPath).catch((e) => {
                message.error(String(e));
              });
            },
          },
          { default: () => "在文件夹中显示" },
        ),
    });
  }

  async function process() {
    if (!canProcess.value) {
      message.warning("请先选择表图和至少 1 张里图");
      return;
    }
    processing.value = true;
    try {
      const res = await invoke<ApngResult>("process_apng", {
        ...basePayload(),
        maxSizeKb: maxSizeKb.value,
        exportDirectory: exportDirectory.value || "",
      });
      showDone(res);
    } catch (e) {
      notification.error({
        title: "动图导出失败",
        content: e instanceof Error ? e.message : String(e),
        duration: 5000,
      });
    } finally {
      processing.value = false;
    }
  }

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer);
  });

  return {
    surfacePath,
    surfaceDelayMs,
    innerFrames,
    loop,
    times,
    compression,
    grayscale,
    maxSizeKb,
    processing,
    previewing,
    previewUrl,
    previewError,
    canProcess,
    filledInners,
    addInner,
    removeInner,
    setInnerPath,
    setInnerDelay,
    setAllDelays,
    reorderInner,
    schedulePreview,
    process,
    exportDirectory,
  };
}
