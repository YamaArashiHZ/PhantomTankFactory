"""
PhantomTank GUI 界面模块
基于 customtkinter 构建的现代化跨平台图形界面

布局概览：
    ┌─────────────────────────────────────────┐
    │  表图 (表面预览)  │  里图 (隐藏预览)      │
    │                   │                      │
    │  [选择表图]       │  [选择里图]           │
    ├─────────────────────────────────────────┤
    │  亮度增强 ──[====]  亮度削减 ──[====]    │
    │  导出目录 [________] [浏览]               │
    ├─────────────────────────────────────────┤
    │  [开始合成]  [打开保存目录]                │
    ├─────────────────────────────────────────┤
    │  ████████████████████░░░░░░░            │
    │  就绪                                    │
    └─────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import Menu, filedialog, messagebox, StringVar, BooleanVar
from typing import Optional

import warnings
import customtkinter as ctk
from PIL import Image, ImageTk

warnings.filterwarnings("ignore", message=".*CTkImage.*")

from config import Config
from logger import init_logger
from image_processor import process_phantom_tank

TEMP_DIR = Path("temp")
THUMB_DIR = Path(os.environ.get("TEMP", "")) / "PhantomTank" / "thumbnails"
THUMB_MAX = 1600  # 缩略图最长边像素

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")


class PhantomTankGUI:
    """幻影坦克主 GUI 窗口"""

    def __init__(self):
        self.config = Config()
        self.logger = init_logger(self.config.debug_mode)
        self.logger.info("PhantomTank GUI 启动")

        self._enable_dpi_awareness()

        self.surface_image: Optional[Image.Image] = None
        self.inner_image: Optional[Image.Image] = None
        self.surface_thumb: Optional[Image.Image] = None
        self.inner_thumb: Optional[Image.Image] = None
        self.last_output_path: Optional[Path] = None
        self._progress_anim_id: str | None = None
        self._progress_value: float = 0.0

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_thumbnails()

        self._setup_window()
        self._build_ui()
        self._load_config_to_ui()

        self.root.update_idletasks()
        self._apply_initial_geometry()

    @staticmethod
    def _enable_dpi_awareness():
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(2)
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("PhantomTank")
        except Exception:
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
                windll.shell32.SetCurrentProcessExplicitAppUserModelID("PhantomTank")
            except Exception:
                pass

    def _cleanup_thumbnails(self):
        """启动时清空缩略图缓存目录（彻底删除，不进回收站）"""
        try:
            if THUMB_DIR.exists():
                shutil.rmtree(str(THUMB_DIR))
            THUMB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _make_thumbnail(self, image: Image.Image) -> Image.Image:
        """为原图生成缩略图，保存到缓存目录并返回内存中的缩略图"""
        thumb = image.copy()
        thumb.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        name = f"{id(image)}_{os.getpid()}.png"
        thumb.save(str(THUMB_DIR / name), "PNG")
        return thumb

    def _setup_window(self):
        self.root = ctk.CTk()
        self.root.title("PhantomTank - 幻影坦克图片合成工具")
        self.root.resizable(True, True)
        self.root.minsize(720, 560)

    def _apply_initial_geometry(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = int(max(860, int(sw * 0.4)) * 0.75)
        h = int(max(640, int(sh * 0.5)) * 0.75)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ==================== UI 构建 ====================

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1, uniform="preview")
        self.root.grid_columnconfigure(1, weight=1, uniform="preview")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)

        # 全局间距
        pad = 8

        self._build_menu()
        self._build_preview_area(pad)
        self._build_settings_area(pad)
        self._build_bottom_bar(pad)

    def _build_menu(self):
        menubar = Menu(self.root, font=("Microsoft YaHei UI", 10))
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0, font=("Microsoft YaHei UI", 10))
        menubar.add_cascade(label=" 文件 ", menu=file_menu)
        file_menu.add_command(label="选择表图...", command=self._select_surface)
        file_menu.add_command(label="选择里图...", command=self._select_inner)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=lambda: self.root.destroy())

        view_menu = Menu(menubar, tearoff=0, font=("Microsoft YaHei UI", 10))
        menubar.add_cascade(label=" 查看 ", menu=view_menu)
        self._appearance_var = StringVar(value="light")
        view_menu.add_radiobutton(
            label="浅色模式", variable=self._appearance_var,
            value="light", command=lambda: self._set_appearance("light"))
        view_menu.add_radiobutton(
            label="暗色模式", variable=self._appearance_var,
            value="dark", command=lambda: self._set_appearance("dark"))

        debug_menu = Menu(menubar, tearoff=0, font=("Microsoft YaHei UI", 10))
        menubar.add_cascade(label=" 调试 ", menu=debug_menu)
        self.debug_var = BooleanVar(value=False)
        debug_menu.add_checkbutton(
            label="启用调试日志", variable=self.debug_var,
            command=self._on_debug_toggle)

    def _set_appearance(self, mode: str):
        ctk.set_appearance_mode(mode)

    def _build_preview_area(self, pad: int):
        """构建左右两个图片预览区"""
        left_frame = self._section_frame("表图 (缩略图 / 封面)", 0, 0, pad)
        right_frame = self._section_frame("里图 (原图 / 点开后可见)", 0, 1, pad)

        label_font = ctk.CTkFont(size=13)

        self.surface_preview_label = ctk.CTkLabel(
            left_frame, text="", font=label_font, text_color="gray50",
        )
        self.surface_preview_label.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(4, 8))

        ctk.CTkButton(
            left_frame, text="选择表图", width=120,
            font=ctk.CTkFont(size=13), corner_radius=8,
            command=self._select_surface,
        ).grid(row=2, column=0, pady=(0, pad))

        self.inner_preview_label = ctk.CTkLabel(
            right_frame, text="", font=label_font, text_color="gray50",
        )
        self.inner_preview_label.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(4, 8))

        ctk.CTkButton(
            right_frame, text="选择里图", width=120,
            font=ctk.CTkFont(size=13), corner_radius=8,
            command=self._select_inner,
        ).grid(row=2, column=0, pady=(0, pad))

        self.surface_preview_label.bind("<Configure>",
                                        lambda e: self._refresh_surface_preview())
        self.inner_preview_label.bind("<Configure>",
                                      lambda e: self._refresh_inner_preview())

    def _section_frame(self, title: str, row: int, col: int, pad: int) -> ctk.CTkFrame:
        """创建带标题的圆角分组区域，左右严格平分宽度"""
        frame = ctk.CTkFrame(self.root, corner_radius=10, border_width=1,
                             border_color=("gray75", "gray30"))
        margin = pad // 2
        frame.grid(row=row, column=col, sticky="nsew",
                   padx=(margin, margin), pady=(pad, pad // 2))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=0)

        ctk.CTkLabel(
            frame, text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=pad + 2, pady=(pad, 2))
        return frame

    def _build_settings_area(self, pad: int):
        """构建设置参数区"""
        settings = ctk.CTkFrame(self.root, corner_radius=10, border_width=1,
                                border_color=("gray75", "gray30"))
        settings.grid(row=1, column=0, columnspan=2, sticky="ew",
                      padx=pad, pady=(0, pad))
        settings.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            settings, text="处理参数",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w",
               padx=pad + 2, pady=(pad, 4))

        row = 1
        entry_font = ctk.CTkFont(size=13)

        # 亮度增强
        ctk.CTkLabel(settings, text="亮度增强 (表图)", font=entry_font).grid(
            row=row, column=0, sticky="w", padx=(pad + 6, pad), pady=6)
        self.slider_enhance = ctk.CTkSlider(
            settings, from_=0, to=100, number_of_steps=10,
            corner_radius=4, button_corner_radius=8,
            command=lambda v: self._on_enhance_change(v),
        )
        self.slider_enhance.grid(row=row, column=1, sticky="ew", padx=(0, pad), pady=6)
        self.brightness_enhance_label = ctk.CTkLabel(
            settings, text="50", width=36, anchor="e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.brightness_enhance_label.grid(row=row, column=2, padx=(0, pad + 4))
        row += 1

        # 亮度削减
        ctk.CTkLabel(settings, text="亮度削减 (里图)", font=entry_font).grid(
            row=row, column=0, sticky="w", padx=(pad + 6, pad), pady=6)
        self.slider_reduce = ctk.CTkSlider(
            settings, from_=-100, to=0, number_of_steps=10,
            corner_radius=4, button_corner_radius=8,
            command=lambda v: self._on_reduce_change(v),
        )
        self.slider_reduce.grid(row=row, column=1, sticky="ew", padx=(0, pad), pady=6)
        self.brightness_reduce_label = ctk.CTkLabel(
            settings, text="-50", width=36, anchor="e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.brightness_reduce_label.grid(row=row, column=2, padx=(0, pad + 4))
        row += 1

        # 分隔线
        sep = ctk.CTkFrame(settings, height=2, fg_color=("gray75", "gray35"))
        sep.grid(row=row, column=0, columnspan=3, sticky="ew",
                 padx=pad + 4, pady=(8, 4))
        row += 1

        # 导出目录
        ctk.CTkLabel(settings, text="导出目录", font=entry_font).grid(
            row=row, column=0, sticky="w", padx=(pad + 6, pad), pady=8)
        self.export_dir_var = StringVar()
        ctk.CTkEntry(
            settings, textvariable=self.export_dir_var,
            font=entry_font, corner_radius=6,
        ).grid(row=row, column=1, sticky="ew", padx=(0, pad), pady=8)
        ctk.CTkButton(
            settings, text="浏览", width=60,
            font=ctk.CTkFont(size=12), corner_radius=6,
            command=self._browse_export_dir,
        ).grid(row=row, column=2, padx=(0, pad + 4), pady=8)

    def _build_bottom_bar(self, pad: int):
        """构建底部按钮区 + 进度条 + 状态"""
        bar = ctk.CTkFrame(self.root, corner_radius=10, border_width=1,
                           border_color=("gray75", "gray30"))
        bar.grid(row=2, column=0, columnspan=2, sticky="ew",
                 padx=pad, pady=(0, pad))
        bar.grid_columnconfigure(0, weight=0)
        bar.grid_columnconfigure(1, weight=0)
        bar.grid_columnconfigure(2, weight=1)

        self.btn_process = ctk.CTkButton(
            bar, text="开始合成", width=100,
            command=self._start_process,
        )
        self.btn_process.grid(row=0, column=0, padx=(pad, 4), pady=pad)

        self.btn_open_folder = ctk.CTkButton(
            bar, text="打开保存目录", width=100,
            command=self._open_save_folder, state="disabled",
        )
        self.btn_open_folder.grid(row=0, column=1, padx=4, pady=pad)

        self.progress_bar = ctk.CTkProgressBar(bar, height=12)
        self.progress_bar.grid(row=0, column=2, sticky="ew",
                               padx=(16, pad), pady=pad)
        self.progress_bar.set(0)

        self.status_var = StringVar(value="就绪")
        ctk.CTkLabel(
            bar, textvariable=self.status_var, anchor="w",
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=0, columnspan=3, sticky="ew",
               padx=pad + 4, pady=(0, pad))

    # ==================== 事件处理 ====================

    def _on_enhance_change(self, value):
        self.brightness_enhance_label.configure(text=str(int(round(value))))

    def _on_reduce_change(self, value):
        self.brightness_reduce_label.configure(text=str(int(round(value))))

    def _on_debug_toggle(self):
        enabled = self.debug_var.get()
        self.logger.info(f"调试模式: {'开启' if enabled else '关闭'}")
        self.config.debug_mode = enabled
        self.config.save()

    def _select_surface(self):
        file_path = filedialog.askopenfilename(
            title="选择表图 (表面预览图)",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if not file_path:
            return
        try:
            self.surface_image = Image.open(file_path)
            self.surface_thumb = self._make_thumbnail(self.surface_image)
            self.logger.info(f"已选择表图: {file_path}")
            self._refresh_surface_preview()
            self._check_ready()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")
            self.logger.error(f"打开表图失败: {e}")

    def _select_inner(self):
        file_path = filedialog.askopenfilename(
            title="选择里图 (隐藏原图)",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if not file_path:
            return
        try:
            self.inner_image = Image.open(file_path)
            self.inner_thumb = self._make_thumbnail(self.inner_image)
            self.logger.info(f"已选择里图: {file_path}")
            self._refresh_inner_preview()
            self._check_ready()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")
            self.logger.error(f"打开里图失败: {e}")

    def _preview_for_label(self, thumb: Image.Image,
                           label: ctk.CTkLabel) -> ImageTk.PhotoImage | None:
        """根据 Label 尺寸从内存缩略图生成预览"""
        max_w = max(label.winfo_width(), 1)
        max_h = max(label.winfo_height(), 1)
        max_w = max(max_w - 10, 10)
        max_h = max(max_h - 10, 10)

        try:
            pw, ph = thumb.size
            if pw > max_w or ph > max_h:
                preview = thumb.copy()
                preview.thumbnail((max_w, max_h), Image.NEAREST)
            else:
                ratio = min(max_w / pw, max_h / ph)
                preview = thumb.resize(
                    (int(pw * ratio), int(ph * ratio)), Image.NEAREST)

            if preview.mode == "RGBA":
                bg = Image.new("RGBA", preview.size, (255, 255, 255, 255))
                bg.paste(preview, (0, 0), preview)
                preview = bg.convert("RGB")

            return ImageTk.PhotoImage(preview)
        except Exception:
            return None

    def _refresh_surface_preview(self):
        if not self.surface_thumb:
            return
        try:
            photo = self._preview_for_label(self.surface_thumb,
                                            self.surface_preview_label)
            if photo:
                self.surface_preview_label.configure(image=photo, text="")
                self.surface_preview_label.image = photo
        except Exception:
            pass

    def _refresh_inner_preview(self):
        if not self.inner_thumb:
            return
        try:
            photo = self._preview_for_label(self.inner_thumb,
                                            self.inner_preview_label)
            if photo:
                self.inner_preview_label.configure(image=photo, text="")
                self.inner_preview_label.image = photo
        except Exception:
            pass

    def _browse_export_dir(self):
        dir_path = filedialog.askdirectory(title="选择导出目录")
        if dir_path:
            self.export_dir_var.set(dir_path)
            self.btn_open_folder.configure(state="normal")
            self.logger.info(f"导出目录设为: {dir_path}")

    def _check_ready(self):
        if self.surface_image and self.inner_image:
            self.status_var.set("表图和里图均已就绪 — 点击「开始合成」")
        elif self.surface_image:
            self.status_var.set("已选择表图，请选择里图")
        elif self.inner_image:
            self.status_var.set("已选择里图，请选择表图")
        else:
            self.status_var.set("请选择表图和里图")

    def _start_process(self):
        if not self.surface_image:
            messagebox.showwarning("提示", "请先选择表图")
            return
        if not self.inner_image:
            messagebox.showwarning("提示", "请先选择里图")
            return
        self._save_config_from_ui()
        self._set_processing_state(True)
        threading.Thread(target=self._run_pipeline, daemon=True).start()

    def _run_pipeline(self):
        try:
            enh = float(self.slider_enhance.get())
            red = float(self.slider_reduce.get())
            export = self.export_dir_var.get().strip()
            output_path = process_phantom_tank(
                surface=self.surface_image,
                inner=self.inner_image,
                brightness_enhancement=enh,
                brightness_reduction=red,
                output_path=export if export else "",
                progress_callback=self._on_progress,
            )
            self.last_output_path = output_path
            self.logger.info(f"合成完成！保存至: {output_path}")
            self.root.after(0, lambda: self._on_process_done(output_path))
        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            self.root.after(0, lambda: self._on_process_error(str(e)))

    def _on_progress(self, step: int, total: int, description: str):
        target = step / total
        self.root.after(0, lambda: self._animate_progress(target, description))

    def _animate_progress(self, target: float, description: str):
        """平滑过渡进度条到目标值"""
        self.status_var.set(f"处理中: {description}")
        diff = target - self._progress_value
        step = max(abs(diff) * 0.25, 0.02)
        self._progress_value += step if diff > 0 else -step
        if abs(self._progress_value - target) < 0.01:
            self._progress_value = target
        self.progress_bar.set(self._progress_value)
        if self._progress_value < target:
            self._progress_anim_id = self.root.after(
                25, lambda: self._animate_progress(target, description))

    def _on_process_done(self, output_path: Path):
        self._progress_value = 1.0
        self.progress_bar.set(1.0)
        self.status_var.set(f"合成完成！保存至: {output_path}")
        self._set_processing_state(False)
        self._show_toast("幻影坦克合成完毕", output_path.name)
        self._open_save_folder()

    def _on_process_error(self, error_msg: str):
        self._set_processing_state(False)
        self.status_var.set(f"处理失败: {error_msg}")
        messagebox.showerror("处理失败", f"合成过程中发生错误:\n{error_msg}")

    def _set_processing_state(self, processing: bool):
        state = "disabled" if processing else "normal"
        self.btn_process.configure(state=state)

    def _open_save_folder(self):
        """打开保存目录；若文件存在则选中，否则仅打开目录"""
        export = self.export_dir_var.get().strip()
        if not export:
            return
        target_dir = Path(export)

        if self.last_output_path and self.last_output_path.exists():
            path_str = str(self.last_output_path.resolve())
            self.logger.info(f"打开并选中文件: {path_str}")
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{path_str}"')
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", path_str])
            else:
                subprocess.run(["xdg-open", str(self.last_output_path.parent)])
        else:
            self.logger.info(f"打开保存目录: {target_dir}")
            if sys.platform == "win32":
                subprocess.run(f'explorer "{target_dir}"')
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target_dir)])
            else:
                subprocess.run(["xdg-open", str(target_dir)])

    def _show_toast(self, title: str, body: str):
        if sys.platform != "win32":
            return
        try:
            from winotify import Notification
        except ImportError:
            self.logger.warning("winotify 未安装，无法发送通知")
            return
        try:
            Notification(app_id="PhantomTank", title=title, msg=body,
                         duration="short").show()
        except Exception as e:
            self.logger.debug(f"Toast 通知发送失败: {e}")

    # ==================== 配置同步 ====================

    def _load_config_to_ui(self):
        self.slider_enhance.set(int(self.config.brightness_enhancement))
        self.slider_reduce.set(int(self.config.brightness_reduction))
        self.export_dir_var.set(self.config.export_directory)
        self.debug_var.set(self.config.debug_mode)
        if self.config.export_directory:
            self.btn_open_folder.configure(state="normal")
        self._on_enhance_change(self.slider_enhance.get())
        self._on_reduce_change(self.slider_reduce.get())

    def _save_config_from_ui(self):
        self.config.brightness_enhancement = float(self.slider_enhance.get())
        self.config.brightness_reduction = float(self.slider_reduce.get())
        self.config.export_directory = self.export_dir_var.get().strip()
        self.config.debug_mode = self.debug_var.get()
        self.config.save()
        self.logger.debug("配置已保存")

    # ==================== 启动 ====================

    def run(self):
        """启动 GUI 主循环，退出时清空缩略图缓存"""
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())
        self.root.mainloop()
        self._cleanup_thumbnails()
