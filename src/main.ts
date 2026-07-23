import { createApp } from "vue";
import App from "./App.vue";
import "./styles/global.css";

/** 禁用页面右键菜单（输入框内保留） */
document.addEventListener(
  "contextmenu",
  (e) => {
    const t = e.target as HTMLElement | null;
    if (t?.closest("input, textarea, [contenteditable='true']")) return;
    e.preventDefault();
  },
  { capture: true },
);

/** 禁止拖拽选中导致的默认拖动行为（图片等） */
document.addEventListener(
  "dragstart",
  (e) => {
    const t = e.target as HTMLElement | null;
    if (t?.closest("input, textarea, [contenteditable='true']")) return;
    e.preventDefault();
  },
  { capture: true },
);

createApp(App).mount("#app");
