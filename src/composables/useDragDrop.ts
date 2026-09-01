import {
  ref,
  onMounted,
  onUnmounted,
  reactive,
  type Ref,
} from "vue";
import { getCurrentWindow } from "@tauri-apps/api/window";

const SUPPORTED_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "bmp",
  "webp",
  "gif",
]);

function isImageFile(path: string): boolean {
  const ext = (path.split(".").pop() ?? "").toLowerCase();
  return SUPPORTED_EXTENSIONS.has(ext);
}

function rectContainsPoint(
  el: HTMLElement,
  physicalX: number,
  physicalY: number,
): boolean {
  const rect = el.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const x = physicalX / dpr;
  const y = physicalY / dpr;
  return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
}

export interface GhostRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export const isGlobalDragActive = ref(false);
export const dragHoles = reactive<Map<symbol, GhostRect>>(new Map());

export function useDragDrop(
  targetRef: Readonly<Ref<HTMLElement | null>>,
  onFileDrop: (path: string) => void,
  enabled?: () => boolean,
) {
  const isDragOver = ref(false);
  const holeKey = Symbol();
  let unlisten: (() => void) | null = null;

  const isEnabled = () => (enabled ? enabled() : true);

  function syncHole() {
    const el = targetRef.value;
    if (!el || !isGlobalDragActive.value || !isEnabled()) {
      dragHoles.delete(holeKey);
      return;
    }
    const r = el.getBoundingClientRect();
    dragHoles.set(holeKey, { x: r.left, y: r.top, w: r.width, h: r.height });
  }

  onMounted(async () => {
    try {
      unlisten = await getCurrentWindow().onDragDropEvent((event) => {
        const { payload } = event;

        if (payload.type === "enter") {
          isGlobalDragActive.value = true;
          syncHole();
        } else if (payload.type === "drop" || payload.type === "leave") {
          isGlobalDragActive.value = false;
          dragHoles.delete(holeKey);
        }

        if (payload.type === "drop") {
          isDragOver.value = false;
          const el = targetRef.value;
          if (
            el &&
            isEnabled() &&
            rectContainsPoint(el, payload.position.x, payload.position.y)
          ) {
            const imageFile = payload.paths.find(isImageFile);
            if (imageFile) onFileDrop(imageFile);
          }
        } else if (payload.type === "enter" || payload.type === "over") {
          const el = targetRef.value;
          isDragOver.value =
            isEnabled() &&
            el != null &&
            rectContainsPoint(el, payload.position.x, payload.position.y);
          syncHole();
        }
      });
    } catch {
      /* 非 Tauri 环境忽略 */
    }
  });

  onUnmounted(() => {
    unlisten?.();
    dragHoles.delete(holeKey);
  });

  return { isDragOver };
}
