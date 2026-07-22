"""
PhantomTank GUI 界面模块
基于 tkinter / ttk 构建的跨平台图形界面

布局概览：
    ┌─────────────────────────────────────────┐
    │  表图 (表面预览)  │  里图 (隐藏预览)      │
    │  [..预览区域..]   │  [..预览区域..]       │
    │  [选择表图]       │  [选择里图]           │
    ├─────────────────────────────────────────┤
    │  亮度增强 ──[====]  亮度削减 ──[====]    │
    │  导出目录 [________] [浏览]               │
    ├─────────────────────────────────────────┤
    │  调试 □   [开始处理]  [打开保存目录]       │
    ├─────────────────────────────────────────┤
    │  进度条 ─────────────────────            │
    │  状态文字                                │
    └─────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import (
    Tk, Toplevel, filedialog, messagebox,
    IntVar, StringVar, BooleanVar,
)
from tkinter import ttk
from typing import Optional

from PIL import Image, ImageTk

from config import Config
from logger import init_logger
from image_processor import process_phantom_tank

# 图片预览最大边长（像素）
PREVIEW_MAX_SIZE = 300

# 临时文件目录
TEMP_DIR = Path("temp")


class PhantomTankGUI:
    """幻影坦克主 GUI 窗口"""

    def __init__(self):
        self.config = Config()
        self.logger = init_logger(self.config.debug_mode)
        self.logger.info("PhantomTank GUI 启动")

        # 图像数据
        self.surface_image: Optional[Image.Image] = None  # 表图原图
        self.inner_image: Optional[Image.Image] = None    # 里图原图
        self.surface_preview: Optional[ImageTk.PhotoImage] = None
        self.inner_preview: Optional[ImageTk.PhotoImage] = None

        # 处理结果
        self.last_output_path: Optional[Path] = None

        # 确保 temp 目录存在
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # 构建界面
        self._setup_window()
        self._build_ui()
        self._load_config_to_ui()

        # 居中显示
        self.root.update_idletasks()
        self._center_window()

    # ==================== 窗口设置 ====================

    def _setup_window(self):
        """创建主窗口并设置基本属性"""
        self.root = Tk()
        self.root.title("PhantomTank - 幻影坦克图片合成工具")
        self.root.resizable(True, True)
        self.root.minsize(640, 500)

        # DPI 感知（Windows）
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # 主题样式
        self.style = ttk.Style(self.root)
        self._setup_styles()

    def _setup_styles(self):
        """配置 ttk 主题样式"""
        available = self.style.theme_names()
        preferred = "vista" if "vista" in available else available[0]
        self.style.theme_use(preferred)

    def _center_window(self):
        """使窗口居中显示"""
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    # ==================== UI 构建 ====================

    def _build_ui(self):
        """构建完整 GUI 布局"""
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)  # 预览区
        self.root.rowconfigure(1, weight=0)  # 参数区
        self.root.rowconfigure(2, weight=0)  # 按钮区
        self.root.rowconfigure(3, weight=0)  # 进度条
        self.root.rowconfigure(4, weight=0)  # 状态

        # 主容器，留出外边距
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, columnspan=2, rowspan=5, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        self._build_preview_area(main_frame)
        self._build_settings_area(main_frame)
        self._build_button_area(main_frame)
        self._build_progress_area(main_frame)

    def _build_preview_area(self, parent: ttk.Frame):
        """构建左右两个图片预览区"""
        # 左侧：表图
        left_frame = ttk.LabelFrame(parent, text="表图 (缩略图 / 封面)", padding=5)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        self.surface_preview_label = ttk.Label(left_frame, text="未选择", anchor="center")
        self.surface_preview_label.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        btn_surface = ttk.Button(left_frame, text="选择表图", command=self._select_surface)
        btn_surface.grid(row=1, column=0, pady=(0, 5))

        # 右侧：里图
        right_frame = ttk.LabelFrame(parent, text="里图 (原图 / 点开后可见)", padding=5)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 5))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        self.inner_preview_label = ttk.Label(right_frame, text="未选择", anchor="center")
        self.inner_preview_label.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        btn_inner = ttk.Button(right_frame, text="选择里图", command=self._select_inner)
        btn_inner.grid(row=1, column=0, pady=(0, 5))

    def _build_settings_area(self, parent: ttk.Frame):
        """构建设置参数区"""
        settings = ttk.LabelFrame(parent, text="处理参数", padding=10)
        settings.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        settings.columnconfigure(1, weight=1)

        row = 0

        # ---- 亮度增强 ----
        ttk.Label(settings, text="亮度增强 (表图)").grid(
            row=row, column=0, sticky="w", padx=(0, 10)
        )
        self.brightness_enhance_var = IntVar(value=50)
        scale_enhance = ttk.Scale(
            settings, from_=0, to=100, orient="horizontal",
            variable=self.brightness_enhance_var,
            command=lambda _: self._on_enhance_change(),
        )
        scale_enhance.grid(row=row, column=1, sticky="ew", padx=(0, 5))
        self.brightness_enhance_label = ttk.Label(settings, text="50", width=4)
        self.brightness_enhance_label.grid(row=row, column=2)
        row += 1

        # ---- 亮度削减 ----
        ttk.Label(settings, text="亮度削减 (里图)").grid(
            row=row, column=0, sticky="w", padx=(0, 10)
        )
        self.brightness_reduce_var = IntVar(value=-50)
        scale_reduce = ttk.Scale(
            settings, from_=-100, to=0, orient="horizontal",
            variable=self.brightness_reduce_var,
            command=lambda _: self._on_reduce_change(),
        )
        scale_reduce.grid(row=row, column=1, sticky="ew", padx=(0, 5))
        self.brightness_reduce_label = ttk.Label(settings, text="-50", width=4)
        self.brightness_reduce_label.grid(row=row, column=2)
        row += 1

        # ---- 导出目录 ----
        ttk.Label(settings, text="导出目录").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=(5, 0)
        )
        dir_frame = ttk.Frame(settings)
        dir_frame.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(5, 0))
        dir_frame.columnconfigure(0, weight=1)

        self.export_dir_var = StringVar()
        export_entry = ttk.Entry(dir_frame, textvariable=self.export_dir_var)
        export_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        btn_browse = ttk.Button(dir_frame, text="浏览...", command=self._browse_export_dir)
        btn_browse.grid(row=0, column=1)
        row += 1

        # ---- 调试模式 ----
        self.debug_var = BooleanVar(value=False)
        debug_cb = ttk.Checkbutton(
            settings, text="调试模式 (启用详细日志文件)", variable=self.debug_var,
        )
        debug_cb.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _build_button_area(self, parent: ttk.Frame):
        """构建下方按钮区"""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        btn_frame.columnconfigure(0, weight=1)

        left_btns = ttk.Frame(btn_frame)
        left_btns.grid(row=0, column=0, sticky="w")

        self.btn_process = ttk.Button(
            left_btns, text="开始合成", command=self._start_process
        )
        self.btn_process.pack(side="left", padx=(0, 10))

        self.btn_open_folder = ttk.Button(
            left_btns, text="打开保存目录", command=self._open_save_folder, state="disabled"
        )
        self.btn_open_folder.pack(side="left")

        self.btn_quit = ttk.Button(btn_frame, text="退出", command=self._on_quit)
        self.btn_quit.grid(row=0, column=1, sticky="e")

    def _build_progress_area(self, parent: ttk.Frame):
        """构建进度条和状态区域"""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 5))
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
        status_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

    # ==================== 事件处理 ====================

    def _on_enhance_change(self):
        """亮度增强滑块变动时更新标签"""
        val = self.brightness_enhance_var.get()
        self.brightness_enhance_label.config(text=str(val))

    def _on_reduce_change(self):
        """亮度削减滑块变动时更新标签"""
        val = self.brightness_reduce_var.get()
        self.brightness_reduce_label.config(text=str(val))

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
            self._update_preview(self.surface_image, self.surface_preview_label)
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
            self._update_preview(self.inner_image, self.inner_preview_label)
            self._check_ready()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")
            self.logger.error(f"打开里图失败: {e}")

    def _update_preview(self, image: Image.Image, label: ttk.Label):
        """在指定 Label 中显示图片缩略图"""
        preview = image.copy()
        preview.thumbnail((PREVIEW_MAX_SIZE, PREVIEW_MAX_SIZE), Image.LANCZOS)

        # 若为 RGBA，在下方铺白底以避免透明显示异常
        if preview.mode == "RGBA":
            bg = Image.new("RGBA", preview.size, (255, 255, 255, 255))
            bg.paste(preview, (0, 0), preview)
            preview = bg.convert("RGB")

        photo = ImageTk.PhotoImage(preview)
        label.config(image=photo, text="")
        label.image = photo  # 保持引用防止被 GC

    def _browse_export_dir(self):
        """浏览并选择导出目录"""
        dir_path = filedialog.askdirectory(title="选择导出目录")
        if dir_path:
            self.export_dir_var.set(dir_path)
            self.logger.info(f"导出目录设为: {dir_path}")

    def _check_ready(self):
        """检查是否已准备好进行合成（表图和里图均已选择）"""
        if self.surface_image and self.inner_image:
            self.status_var.set("表图和里图均已就绪，点击「开始合成」继续")
        else:
            if self.surface_image:
                self.status_var.set("已选择表图，请选择里图")
            elif self.inner_image:
                self.status_var.set("已选择里图，请选择表图")
            else:
                self.status_var.set("请选择表图和里图")

    def _start_process(self):
        """用户点击开始合成按钮"""
        if not self.surface_image:
            messagebox.showwarning("提示", "请先选择表图")
            return
        if not self.inner_image:
            messagebox.showwarning("提示", "请先选择里图")
            return

        # 确认对话框
        enh = self.brightness_enhance_var.get()
        red = self.brightness_reduce_var.get()
        exp = self.export_dir_var.get() or "当前目录"

        confirmed = messagebox.askokcancel(
            "确认合成",
            f"即将开始合成幻影坦克：\n\n"
            f"  亮度增强 (表图): {enh}\n"
            f"  亮度削减 (里图): {red}\n"
            f"  导出位置: {exp}\n\n"
            f"确认继续？",
        )
        if not confirmed:
            return

        # 保存配置
        self._save_config_from_ui()

        # 禁用按钮，防止重复点击
        self._set_processing_state(True)

        # 在新线程中运行耗时处理
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

            # GUI 更新须回到主线程
            self.root.after(0, lambda: self._on_process_done(output_path))

        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            self.root.after(0, lambda: self._on_process_error(str(e)))

    def _on_progress(self, step: int, total: int, description: str):
        """进度回调（来自后台线程，需线程安全地更新 GUI）"""
        percent = int(step / total * 100)
        self.root.after(0, lambda: self._update_progress(percent, description))

    def _update_progress(self, percent: int, description: str):
        """主线程中更新进度条和状态"""
        self.progress_var.set(percent)
        self.status_var.set(f"处理中: {description} ({percent}%)")

    def _on_process_done(self, output_path: Path):
        """处理完成后的 GUI 更新"""
        self.progress_var.set(100)
        self.status_var.set(f"合成完成！保存至: {output_path}")
        self.btn_open_folder.config(state="normal")
        self._set_processing_state(False)

        # 弹出完成提示
        result = messagebox.askyesno(
            "合成完成",
            f"幻影坦克已合成完毕！\n\n文件: {output_path.name}\n\n是否打开保存目录？",
        )
        if result:
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
            self.btn_open_folder.config(state="normal" if self.last_output_path else "disabled")

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

    def _on_quit(self):
        """退出程序前确认"""
        if messagebox.askokcancel("退出", "确定要退出 PhantomTank 吗？"):
            self.logger.info("用户退出程序")
            self.root.destroy()

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
        """将 UI 中的参数保存到配置对象并写入 YAML"""
        self.config.brightness_enhancement = float(self.brightness_enhance_var.get())
        self.config.brightness_reduction = float(self.brightness_reduce_var.get())
        self.config.export_directory = self.export_dir_var.get().strip()
        self.config.debug_mode = self.debug_var.get()
        self.config.save()
        self.logger.debug("配置已保存")

    # ==================== 启动 ====================

    def run(self):
        """启动 GUI 主循环"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.root.mainloop()
