"""
PhantomTank GUI 界面模块
基于 tkinter / ttk 构建的跨平台图形界面，针对 4K 高 DPI 显示优化

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
    │  进度条 ─────────────────────            │
    │  状态文字                                │
    └─────────────────────────────────────────┘
"""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from tkinter import (
    Tk, Menu, filedialog, messagebox,
    IntVar, StringVar, BooleanVar,
)
from tkinter import ttk
from typing import Optional

from PIL import Image, ImageTk

from config import Config
from logger import init_logger
from image_processor import process_phantom_tank

TEMP_DIR = Path("temp")

# 基础字号（会根据 DPI 缩放）
BASE_FONT_SIZE = 11
BASE_HEADING_SIZE = 13


class PhantomTankGUI:
    """幻影坦克主 GUI 窗口"""

    def __init__(self):
        self.config = Config()
        self.logger = init_logger(self.config.debug_mode)
        self.logger.info("PhantomTank GUI 启动")

        # 图像数据
        self.surface_image: Optional[Image.Image] = None
        self.inner_image: Optional[Image.Image] = None

        # 处理结果
        self.last_output_path: Optional[Path] = None

        # 确保 temp 目录存在
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # 构建界面
        self._setup_window()
        self._build_ui()
        self._load_config_to_ui()

        # 初始尺寸：屏幕的 40% 宽、50% 高，适配 4K
        self.root.update_idletasks()
        self._apply_initial_geometry()

    # ==================== 窗口设置 ====================

    def _setup_window(self):
        """创建主窗口并设置基本属性"""
        self.root = Tk()
        self.root.title("PhantomTank - 幻影坦克图片合成工具")
        self.root.resizable(True, True)
        self.root.minsize(640, 500)

        # 高 DPI / 4K 感知 (Windows)
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(2)
            # 注册 AppUserModelID，使 Toast 通知点击生效
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("PhantomTank")
        except Exception:
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
                windll.shell32.SetCurrentProcessExplicitAppUserModelID("PhantomTank")
            except Exception:
                pass

        # 主题与字体缩放
        self.style = ttk.Style(self.root)
        available = self.style.theme_names()
        preferred = "vista" if "vista" in available else available[0]
        self.style.theme_use(preferred)

        # 计算 DPI 缩放因子
        self._dpi_scale = max(self.root.tk.call("tk", "scaling") or 1.0, 1.0)

        self._setup_styles()

    def _setup_styles(self):
        """配置全局字体与控件样式（根据 DPI 缩放）"""
        scale = self._dpi_scale
        default_font = ("Microsoft YaHei UI", int(BASE_FONT_SIZE * scale))
        heading_font = ("Microsoft YaHei UI", int(BASE_HEADING_SIZE * scale), "bold")
        mono_font = ("Consolas", int(BASE_FONT_SIZE * scale))

        self.style.configure(".", font=default_font)

        # 标签
        self.style.configure("TLabel", font=default_font, padding=2)
        self.style.configure("Heading.TLabel", font=heading_font)

        # 按钮（加大内边距）
        self.style.configure(
            "TButton", font=default_font,
            padding=(int(12 * scale), int(6 * scale)),
        )

        # 输入框
        self.style.configure("TEntry", font=default_font, padding=int(4 * scale))

        # LabelFrame 标题
        self.style.configure(
            "TLabelframe.Label", font=heading_font,
        )

        # 进度条（加高）
        self.style.configure(
            "TProgressbar",
            thickness=int(22 * scale),
        )

        # Checkbutton
        self.style.configure("TCheckbutton", font=default_font, padding=4)

        # 菜单栏字体
        self.root.option_add("*Menu*Font", default_font)

        # 保存字型引用
        self._fonts = {
            "default": default_font,
            "heading": heading_font,
            "mono": mono_font,
        }

    def _apply_initial_geometry(self):
        """设置初始窗口大小（基于屏幕尺寸按比例缩放）"""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = max(800, int(sw * 0.4))
        h = max(600, int(sh * 0.5))
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ==================== UI 构建 ====================

    def _build_ui(self):
        """构建完整 GUI 布局"""
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=0)
        self.root.rowconfigure(3, weight=0)
        self.root.rowconfigure(4, weight=0)

        # 菜单栏（调试模式藏在这里）
        self._build_menu()

        # 主容器
        padding = int(12 * self._dpi_scale)
        main_frame = ttk.Frame(self.root, padding=padding)
        main_frame.grid(row=0, column=0, columnspan=2, rowspan=5, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=0)
        main_frame.rowconfigure(3, weight=0)

        self._build_preview_area(main_frame)
        self._build_settings_area(main_frame)
        self._build_button_area(main_frame)
        self._build_progress_area(main_frame)

    def _build_menu(self):
        """构建菜单栏"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择表图...", command=self._select_surface)
        file_menu.add_command(label="选择里图...", command=self._select_inner)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=lambda: self.root.destroy())

        debug_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="调试", menu=debug_menu)
        self.debug_var = BooleanVar(value=False)
        debug_menu.add_checkbutton(
            label="启用调试日志", variable=self.debug_var,
            command=self._on_debug_toggle,
        )

    def _build_preview_area(self, parent: ttk.Frame):
        """构建左右两个图片预览区（高度随窗口缩放）"""
        pad = int(8 * self._dpi_scale)

        # 左侧：表图
        left_frame = ttk.LabelFrame(parent, text="表图 (缩略图 / 封面)", padding=pad)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, pad // 2), pady=(0, pad))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=0)

        self.surface_preview_label = ttk.Label(
            left_frame, text="未选择\n\n\n\n\n\n\n\n\n\n", anchor="center",
            background="#e0e0e0",
        )
        self.surface_preview_label.grid(row=0, column=0, sticky="nsew", pady=(0, pad // 2))

        btn_surface = ttk.Button(left_frame, text="选择表图", command=self._select_surface)
        btn_surface.grid(row=1, column=0, pady=(0, pad // 2))

        # 右侧：里图
        right_frame = ttk.LabelFrame(parent, text="里图 (原图 / 点开后可见)", padding=pad)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(pad // 2, 0), pady=(0, pad))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=0)

        self.inner_preview_label = ttk.Label(
            right_frame, text="未选择\n\n\n\n\n\n\n\n\n\n", anchor="center",
            background="#e0e0e0",
        )
        self.inner_preview_label.grid(row=0, column=0, sticky="nsew", pady=(0, pad // 2))

        btn_inner = ttk.Button(right_frame, text="选择里图", command=self._select_inner)
        btn_inner.grid(row=1, column=0, pady=(0, pad // 2))

        # 窗口大小变化时动态刷新预览
        self.surface_preview_label.bind("<Configure>", lambda e: self._refresh_surface_preview())
        self.inner_preview_label.bind("<Configure>", lambda e: self._refresh_inner_preview())

    def _build_settings_area(self, parent: ttk.Frame):
        """构建设置参数区"""
        pad = int(10 * self._dpi_scale)
        settings = ttk.LabelFrame(parent, text="处理参数", padding=pad)
        settings.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, pad))
        settings.columnconfigure(1, weight=1)

        row = 0
        gap = int(6 * self._dpi_scale)

        # ---- 亮度增强 ----
        ttk.Label(settings, text="亮度增强 (表图)").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=gap
        )
        self.brightness_enhance_var = IntVar(value=50)
        scale_enhance = ttk.Scale(
            settings, from_=0, to=100, orient="horizontal",
            variable=self.brightness_enhance_var,
            command=lambda _: self._on_enhance_change(),
        )
        scale_enhance.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=gap)
        self.brightness_enhance_label = ttk.Label(settings, text="50", width=4)
        self.brightness_enhance_label.grid(row=row, column=2, pady=gap)
        row += 1

        # ---- 亮度削减 ----
        ttk.Label(settings, text="亮度削减 (里图)").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=gap
        )
        self.brightness_reduce_var = IntVar(value=-50)
        scale_reduce = ttk.Scale(
            settings, from_=-100, to=0, orient="horizontal",
            variable=self.brightness_reduce_var,
            command=lambda _: self._on_reduce_change(),
        )
        scale_reduce.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=gap)
        self.brightness_reduce_label = ttk.Label(settings, text="-50", width=4)
        self.brightness_reduce_label.grid(row=row, column=2, pady=gap)
        row += 1

        # ---- 导出目录 ----
        ttk.Label(settings, text="导出目录").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=(gap + 5, 0)
        )
        dir_frame = ttk.Frame(settings)
        dir_frame.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(gap + 5, 0))
        dir_frame.columnconfigure(0, weight=1)

        self.export_dir_var = StringVar()
        export_entry = ttk.Entry(dir_frame, textvariable=self.export_dir_var)
        export_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        btn_browse = ttk.Button(dir_frame, text="浏览...", command=self._browse_export_dir)
        btn_browse.grid(row=0, column=1)

    def _build_button_area(self, parent: ttk.Frame):
        """构建下方按钮区"""
        pad = int(10 * self._dpi_scale)
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, pad))

        self.btn_process = ttk.Button(
            btn_frame, text="开始合成", command=self._start_process
        )
        self.btn_process.pack(side="left", padx=(0, 10))

        self.btn_open_folder = ttk.Button(
            btn_frame, text="打开保存目录", command=self._open_save_folder, state="disabled"
        )
        self.btn_open_folder.pack(side="left")

    def _build_progress_area(self, parent: ttk.Frame):
        """构建进度条和状态区域"""
        pad = int(6 * self._dpi_scale)
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, pad))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_var = IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, mode="determinate",
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.status_var = StringVar(value="就绪")
        status_label = ttk.Label(
            progress_frame, textvariable=self.status_var, anchor="w",
        )
        status_label.grid(row=1, column=0, sticky="w", pady=(pad // 2, 0))

    # ==================== 事件处理 ====================

    def _on_enhance_change(self):
        self.brightness_enhance_label.config(text=str(self.brightness_enhance_var.get()))

    def _on_reduce_change(self):
        self.brightness_reduce_label.config(text=str(self.brightness_reduce_var.get()))

    def _on_debug_toggle(self):
        enabled = self.debug_var.get()
        self.logger.info(f"调试模式: {'开启' if enabled else '关闭'}")
        self.config.debug_mode = enabled
        self.config.save()

    def _select_surface(self):
        """选择表图并显示预览"""
        file_path = filedialog.askopenfilename(
            title="选择表图 (表面预览图)",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            self.surface_image = Image.open(file_path)
            self.logger.info(f"已选择表图: {file_path}")
            self._refresh_surface_preview()
            self._check_ready()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")
            self.logger.error(f"打开表图失败: {e}")

    def _select_inner(self):
        """选择里图并显示预览"""
        file_path = filedialog.askopenfilename(
            title="选择里图 (隐藏原图)",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            self.inner_image = Image.open(file_path)
            self.logger.info(f"已选择里图: {file_path}")
            self._refresh_inner_preview()
            self._check_ready()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")
            self.logger.error(f"打开里图失败: {e}")

    def _preview_for_label(self, image: Image.Image, label: ttk.Label) -> ImageTk.PhotoImage:
        """根据 Label 当前可用尺寸生成缩略图"""
        max_w = max(label.winfo_width(), 1)
        max_h = max(label.winfo_height(), 1)
        max_w = max(max_w - 10, 50)
        max_h = max(max_h - 10, 50)

        preview = image.copy()
        preview.thumbnail((max_w, max_h), Image.NEAREST)

        if preview.mode == "RGBA":
            bg = Image.new("RGBA", preview.size, (255, 255, 255, 255))
            bg.paste(preview, (0, 0), preview)
            preview = bg.convert("RGB")

        return ImageTk.PhotoImage(preview)

    def _refresh_surface_preview(self):
        if not self.surface_image:
            return
        try:
            photo = self._preview_for_label(self.surface_image, self.surface_preview_label)
            self.surface_preview_label.config(image=photo, text="")
            self.surface_preview_label.image = photo
        except Exception:
            pass

    def _refresh_inner_preview(self):
        if not self.inner_image:
            return
        try:
            photo = self._preview_for_label(self.inner_image, self.inner_preview_label)
            self.inner_preview_label.config(image=photo, text="")
            self.inner_preview_label.image = photo
        except Exception:
            pass

    def _browse_export_dir(self):
        """浏览并选择导出目录"""
        dir_path = filedialog.askdirectory(title="选择导出目录")
        if dir_path:
            self.export_dir_var.set(dir_path)
            self.logger.info(f"导出目录设为: {dir_path}")

    def _check_ready(self):
        """检查是否已准备好进行合成"""
        if self.surface_image and self.inner_image:
            self.status_var.set("表图和里图均已就绪，点击「开始合成」继续")
        elif self.surface_image:
            self.status_var.set("已选择表图，请选择里图")
        elif self.inner_image:
            self.status_var.set("已选择里图，请选择表图")
        else:
            self.status_var.set("请选择表图和里图")

    def _start_process(self):
        """用户点击开始合成按钮（直接执行）"""
        if not self.surface_image:
            messagebox.showwarning("提示", "请先选择表图")
            return
        if not self.inner_image:
            messagebox.showwarning("提示", "请先选择里图")
            return

        self._save_config_from_ui()
        self._set_processing_state(True)

        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self):
        """在后台线程中执行图像处理流水线"""
        try:
            enh = float(self.brightness_enhance_var.get())
            red = float(self.brightness_reduce_var.get())
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
        """进度回调（后台线程 → 主线程）"""
        percent = int(step / total * 100)
        self.root.after(0, lambda: self._update_progress(percent, description))

    def _update_progress(self, percent: int, description: str):
        """主线程中更新进度条和状态"""
        self.progress_var.set(percent)
        self.status_var.set(f"处理中: {description}")

    def _on_process_done(self, output_path: Path):
        """处理完成后的 GUI 更新 + 自动打开目录"""
        self.progress_var.set(100)
        self.status_var.set(f"合成完成！保存至: {output_path}")
        self.btn_open_folder.config(state="normal")
        self._set_processing_state(False)
        self._show_toast("幻影坦克合成完毕", output_path.name)
        # 合成完成后自动打开保存目录
        self._open_save_folder()

    def _on_process_error(self, error_msg: str):
        """处理失败后的 GUI 更新"""
        self._set_processing_state(False)
        self.status_var.set(f"处理失败: {error_msg}")
        messagebox.showerror("处理失败", f"合成过程中发生错误:\n{error_msg}")

    def _set_processing_state(self, processing: bool):
        """切换按钮的可点击状态"""
        state = "disabled" if processing else "normal"
        self.btn_process.config(state=state)
        if not processing:
            self.btn_open_folder.config(
                state="normal" if self.last_output_path else "disabled"
            )

    def _open_save_folder(self):
        """打开上次保存文件所在的目录"""
        if self.last_output_path and self.last_output_path.exists():
            path_str = str(self.last_output_path.resolve())
            self.logger.info(f"打开保存目录: {path_str}")
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{path_str}"')
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", path_str])
            else:
                subprocess.run(["xdg-open", str(self.last_output_path.parent)])
        else:
            messagebox.showinfo("提示", "尚未生成输出文件")

    # ==================== Windows 通知 ====================

    def _show_toast(self, title: str, body: str):
        """
        触发 Windows Toast 通知（纯信息提示）。
        """
        if sys.platform != "win32":
            return

        try:
            from winotify import Notification
        except ImportError:
            self.logger.warning("winotify 未安装，无法发送通知。运行 pip install winotify 以启用。")
            return

        try:
            toast = Notification(
                app_id="PhantomTank",
                title=title,
                msg=body,
                duration="short",
            )
            toast.show()
        except Exception as e:
            self.logger.debug(f"Toast 通知发送失败: {e}")

    # ==================== 配置同步 ====================

    def _load_config_to_ui(self):
        """将当前配置加载到 UI 控件中"""
        self.brightness_enhance_var.set(int(self.config.brightness_enhancement))
        self.brightness_reduce_var.set(int(self.config.brightness_reduction))
        self.export_dir_var.set(self.config.export_directory)
        self.debug_var.set(self.config.debug_mode)

        self._on_enhance_change()
        self._on_reduce_change()

    def _save_config_from_ui(self):
        """将 UI 参数保存到配置对象并写入 YAML"""
        self.config.brightness_enhancement = float(self.brightness_enhance_var.get())
        self.config.brightness_reduction = float(self.brightness_reduce_var.get())
        self.config.export_directory = self.export_dir_var.get().strip()
        self.config.debug_mode = self.debug_var.get()
        self.config.save()
        self.logger.debug("配置已保存")

    # ==================== 启动 ====================

    def run(self):
        """启动 GUI 主循环，关闭时直接退出"""
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())
        self.root.mainloop()
