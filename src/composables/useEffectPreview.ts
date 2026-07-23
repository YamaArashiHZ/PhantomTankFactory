import { computed, onBeforeUnmount, ref, watch, type Ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { PREVIEW_QUALITY_EDGE, type PreviewResult } from "../types";
import { useAppConfig } from "./useAppConfig";

/** 预览防抖间隔（拖动滑条停止后再请求） */
const PREVIEW_DEBOUNCE_MS = 280;

/**
 * 实时效果预览：监听表/里图路径与亮度、清晰度、启用开关，
 * 防抖调用 Rust 合成并回传白底/黑底 dataURL。
 */
export function useEffectPreview(
  surfacePath: Ref<string | null>,
  innerPath: Ref<string | null>,
) {
  const {
    brightnessEnhancement,
    brightnessReduction,
    previewQuality,
    previewEnabled,
  } = useAppConfig();

  const surfaceEffectUrl = ref<string | null>(null);
  const innerEffectUrl = ref<string | null>(null);
  const previewLoading = ref(false);
  const previewError = ref<string | null>(null);

  let previewTimer: ReturnType<typeof setTimeout> | null = null;
  /** 序号防乱序：新请求使旧请求结果作废 */
  let previewSeq = 0;

  const previewReady = computed(
    () => !!surfacePath.value && !!innerPath.value,
  );

  function clearPreview() {
    surfaceEffectUrl.value = null;
    innerEffectUrl.value = null;
    previewError.value = null;
    previewLoading.value = false;
  }

  async function runPreview() {
    if (!previewEnabled.value || !surfacePath.value || !innerPath.value) {
      clearPreview();
      return;
    }

    const seq = ++previewSeq;
    previewLoading.value = true;
    previewError.value = null;

    try {
      const edge =
        PREVIEW_QUALITY_EDGE[previewQuality.value] ?? PREVIEW_QUALITY_EDGE.medium;
      const result = await invoke<PreviewResult>("preview_phantom_tank", {
        surfacePath: surfacePath.value,
        innerPath: innerPath.value,
        brightnessEnhancement: brightnessEnhancement.value,
        brightnessReduction: brightnessReduction.value,
        maxEdge: edge,
      });
      if (seq !== previewSeq) return;
      surfaceEffectUrl.value = result.surfacePreview;
      innerEffectUrl.value = result.innerPreview;
    } catch (e) {
      if (seq !== previewSeq) return;
      previewError.value = e instanceof Error ? e.message : String(e);
      surfaceEffectUrl.value = null;
      innerEffectUrl.value = null;
    } finally {
      if (seq === previewSeq) {
        previewLoading.value = false;
      }
    }
  }

  function schedulePreview() {
    if (previewTimer) clearTimeout(previewTimer);
    if (!previewEnabled.value || !surfacePath.value || !innerPath.value) {
      previewSeq += 1;
      clearPreview();
      return;
    }
    previewTimer = setTimeout(() => {
      void runPreview();
    }, PREVIEW_DEBOUNCE_MS);
  }

  watch(
    [
      surfacePath,
      innerPath,
      brightnessEnhancement,
      brightnessReduction,
      previewQuality,
      previewEnabled,
    ],
    () => schedulePreview(),
    { immediate: true },
  );

  onBeforeUnmount(() => {
    if (previewTimer) clearTimeout(previewTimer);
    previewSeq += 1;
  });

  return {
    surfaceEffectUrl,
    innerEffectUrl,
    previewLoading,
    previewError,
    previewReady,
  };
}
