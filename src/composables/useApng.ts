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

/** 生成稳定的帧 id */
let frameSeq = 0;
function newFrameId() {
  return `f${++frameSeq}`;
}

export function useApng() {
  const message = useMessage();
  const notification = useNotification();
  const { exportDirectory } = useAppConfig();

  const surfacePath = ref<string | null>(null);
  const surfaceDelayMs = ref(DEFAULT_DELAY_MS);

  /** 里图是否统一显示时间 */
  const unifiedDelay = ref(false);
  /** 统一显示时长（ms） */
  const unifiedDelayMs = ref(DEFAULT_DELAY_MS);

  const innerFrames = ref<ApngInnerFrame[]>([
    { id: newFrameId(), path: null, delayMs: DEFAULT_DELAY_MS },
  ]);

  const loop = ref<ApngLoop>("infinite");
  const times = ref(3);
  const compression = ref(6);
  const grayscale = ref(false);
  /** 成品大小上限（KB）；null = 不限制 */
  const maxSizeKb = ref<number | null>(null);

  const processing = ref(false);
  const previewing = ref(false);
  const frames = ref<string[]>([]);
  const delaysMs = ref<number[]>([]);
  const currentFrame = ref(0);
  const playing = ref(false);
  const previewError = ref<string | null>(null);
  /** 当前播放/显示的帧 */
  const previewSrc = computed(() => frames.value[currentFrame.value] ?? null);

  const filledInners = computed(
    () => innerFrames.value.filter((f) => f.path).length,
  );
  const canProcess = computed(
    () => !!surfacePath.value && filledInners.value >= 1,
  );

  function addInner(path?: string | null) {
    innerFrames.value.push({ id: newFrameId(), path: path ?? null, delayMs: DEFAULT_DELAY_MS });
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
      .map((f) => (unifiedDelay.value ? unifiedDelayMs.value : f.delayMs));
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
  let playTimer: ReturnType<typeof setTimeout> | null = null;
  /** 预览代数：变更时递增，使旧预览任务的结果失效（取消） */
  let previewSeq = 0;
  async function runPreview() {
    const seq = previewSeq;
    if (!canProcess.value) {
      frames.value = [];
      delaysMs.value = [];
      currentFrame.value = 0;
      playing.value = false;
      previewError.value = null;
      previewing.value = false;
      return;
    }
    previewing.value = true;
    previewError.value = null;
    try {
      const res = await invoke<ApngPreviewResult>("preview_apng", {
        ...basePayload(),
        maxEdge: PREVIEW_EDGE,
      });
      if (seq !== previewSeq) return; // 过期结果，丢弃
      frames.value = res.frames;
      delaysMs.value = res.delaysMs;
      currentFrame.value = 0;
      playing.value = false;
      previewing.value = false;
    } catch (e) {
      if (seq !== previewSeq) return;
      previewError.value = e instanceof Error ? e.message : String(e);
      frames.value = [];
      delaysMs.value = [];
      previewing.value = false;
    }
  }
  function schedulePreview() {
    // 取消进行中的预览：使旧任务结果失效
    previewSeq += 1;
    // 重新渲染期间：立即隐藏旧帧并显示加载
    previewing.value = true;
    frames.value = [];
    previewError.value = null;
    if (playTimer) {
      clearTimeout(playTimer);
      playTimer = null;
    }
    playing.value = false;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void runPreview(), PREVIEW_DEBOUNCE_MS);
  }

  function stopPlay() {
    if (playTimer) {
      clearTimeout(playTimer);
      playTimer = null;
    }
    playing.value = false;
  }
  function nextFrame() {
    const n = frames.value.length;
    if (n > 1) currentFrame.value = (currentFrame.value + 1) % n;
    else stopPlay();
  }
  function prevFrame() {
    const n = frames.value.length;
    if (n > 1) currentFrame.value = (currentFrame.value - 1 + n) % n;
  }
  /** 按当前帧的设定时长推进播放 */
  function playTick() {
    nextFrame();
    if (!playing.value) return;
    const d = delaysMs.value[currentFrame.value] ?? 600;
    playTimer = setTimeout(playTick, d);
  }
  function togglePlay() {
    if (playing.value) {
      stopPlay();
      return;
    }
    if (frames.value.length < 2) return;
    playing.value = true;
    const d = delaysMs.value[currentFrame.value] ?? 600;
    playTimer = setTimeout(playTick, d);
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
    if (playTimer) clearTimeout(playTimer);
  });

  return {
    surfacePath,
    surfaceDelayMs,
    unifiedDelay,
    unifiedDelayMs,
    innerFrames,
    loop,
    times,
    compression,
    grayscale,
    maxSizeKb,
    processing,
    previewing,
    frames,
    currentFrame,
    playing,
    previewSrc,
    previewError,
    canProcess,
    filledInners,
    addInner,
    removeInner,
    setInnerPath,
    setInnerDelay,
    reorderInner,
    schedulePreview,
    nextFrame,
    prevFrame,
    togglePlay,
    process,
    exportDirectory,
  };
}
