"""
PhantomTank GUI 界面模块
基于 customtkinter 构建的现代化图形界面，左侧图标导航栏 + 无边框窗口
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, StringVar
import warnings
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from config import Config
from logger import init_logger
from image_processor import process_phantom_tank
from icons import get_icons

TEMP_DIR = Path("temp")
THUMB_DIR = Path(os.environ.get("TEMP", "")) / "PhantomTank" / "thumbnails"
THUMB_MAX = 800  # 缩略图最长边像素

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")
warnings.filterwarnings("ignore", message=".*CTkImage.*")

NAV_WIDTH = 56  # 导航栏宽度


class PhantomTankGUI:
    """幻影坦克主 GUI 窗口"""

    def __init__(self, debug_mode: bool = False):
        self.config = Config()
        self.logger = init_logger(debug_mode)
        self.logger.info("PhantomTank GUI 启动")

        self._enable_dpi_awareness()

        self.surface_image: Optional[Image.Image] = None
        self.inner_image: Optional[Image.Image] = None
        self.surface_thumb: Optional[Image.Image] = None
        self.inner_thumb: Optional[Image.Image] = None
        self.last_output_path: Optional[Path] = None
        self._progress_anim_id: str | None = None
        self._progress_value: float = 0.0
        self._preview_surface_img: Optional[Image.Image] = None
        self._preview_inner_img: Optional[Image.Image] = None
        self._icons: dict[str, ctk.CTkImage] = {}
        self._current_page: str = "home"

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_thumbnails()

        self._setup_window()
        self._build_nav_bar()
        self._build_pages()
        self._load_config_to_ui()

        self.root.update_idletasks()
        self._apply_initial_geometry()
        self._show_page("home")

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
        try:
            if THUMB_DIR.exists():
                shutil.rmtree(str(THUMB_DIR))
            THUMB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _make_thumbnail(self, image: Image.Image) -> Image.Image:
        thumb = image.copy()
        thumb.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        name = f"{id(image)}_{os.getpid()}.png"
        thumb.save(str(THUMB_DIR / name), "PNG")
        return thumb

    # ==================== 窗口设置 ====================

    def _setup_window(self):
        self.root = ctk.CTk()
        self.root.title("PhantomTankFactory")
        self.root.resizable(True, True)
        self.root.minsize(640, 500)

        icon_path = Path(__file__).resolve().parent / "assets" / "icons" / "PhantomTankFactorySmall.png"
        if icon_path.exists():
            self.root.iconphoto(True, tk.PhotoImage(file=str(icon_path)))


    def _apply_initial_geometry(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = int(max(860, int(sw * 0.4)) * 0.75)
        h = int(max(640, int(sh * 0.5)) * 0.75)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ==================== 导航栏 ====================

    def _build_nav_bar(self):
        self.nav_frame = ctk.CTkFrame(
            self.root, width=NAV_WIDTH, corner_radius=0,
            fg_color=("gray90", "gray17"),
        )
        self.nav_frame.pack(side="left", fill="y")
        self.nav_frame.pack_propagate(False)

        self._load_icons()

        # 主页按钮（向上对齐）
        self.btn_home = ctk.CTkButton(
            self.nav_frame, text="", image=self._icons["home"],
            width=40, height=40, fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=lambda: self._show_page("home"),
        )
        self.btn_home.pack(side="top", pady=(8, 2))

        self.btn_preview = ctk.CTkButton(
            self.nav_frame, text="", image=self._icons["preview"],
            width=40, height=40, fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=lambda: self._show_page("preview"),
        )
        self.btn_preview.pack(side="top", pady=2)

        # 底部区域
        bottom = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=8)

        self.btn_theme = ctk.CTkButton(
            bottom, text="", image=self._icons["theme"],
            width=40, height=40, fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=self._toggle_theme,
        )
        self.btn_theme.pack(side="top", pady=2)

        self.btn_about = ctk.CTkButton(
            bottom, text="", image=self._icons["about"],
            width=40, height=40, fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=lambda: self._show_page("about"),
        )
        self.btn_about.pack(side="top", pady=2)

    def _load_icons(self):
        pil_icons = get_icons(ctk.get_appearance_mode() == "Light")
        for name, pil_img in pil_icons.items():
            self._icons[name] = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(24, 24))

    def _refresh_icons(self):
        self._load_icons()
        self.btn_home.configure(image=self._icons["home"])
        self.btn_preview.configure(image=self._icons["preview"])
        self.btn_theme.configure(image=self._icons["theme"])
        self.btn_about.configure(image=self._icons["about"])

    # ==================== 页面系统 ====================

    def _build_pages(self):
        self.content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True)

        # 主页
        self.page_home = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.page_home.grid_columnconfigure(0, weight=1, uniform="preview")
        self.page_home.grid_columnconfigure(1, weight=1, uniform="preview")
        self.page_home.grid_rowconfigure(0, weight=1)
        self.page_home.grid_rowconfigure(1, weight=0)
        self.page_home.grid_rowconfigure(2, weight=0)

        # 关于页
        self.page_about = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        # 预览页
        self.page_preview = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        self._build_page_home()
        self._build_page_about()
        self._build_page_preview()

    def _show_page(self, name: str):
        for p in (self.page_home, self.page_about, self.page_preview):
            p.pack_forget()
        if name == "home":
            self.page_home.pack(fill="both", expand=True, padx=6, pady=6)
        elif name == "preview":
            self.page_preview.pack(fill="both", expand=True, padx=6, pady=6)
        else:
            self.page_about.pack(fill="both", expand=True)
        self._current_page = name
        self._update_nav_active()

    def _update_nav_active(self):
        active_color = ("gray75", "gray30")
        for btn, page in [(self.btn_home, "home"), (self.btn_preview, "preview"),
                          (self.btn_about, "about")]:
            if self._current_page == page:
                btn.configure(fg_color=active_color)
            else:
                btn.configure(fg_color="transparent")

    # ==================== 主页 ====================

    def _build_page_home(self):
        """构建主页内容（原 _build_ui 内容）"""
        pad = 6
        self._build_preview_area(pad)
        self._build_settings_area(pad)
        self._build_bottom_bar(pad)

    def _build_page_about(self):
        """构建关于页面"""
        about = self.page_about
        about.grid_rowconfigure(0, weight=1)
        about.grid_rowconfigure(1, weight=1)
        about.grid_rowconfigure(2, weight=1)
        about.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            about, text="PhantomTankFactory",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="s", pady=(0, 4))

        ctk.CTkLabel(
            about, text="幻影坦克图片合成工具",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=0, sticky="n", pady=(4, 16))

        info_frame = ctk.CTkFrame(about, fg_color="transparent")
        info_frame.grid(row=2, column=0, sticky="n")
        lines = [
            ("版本号", "2.0.0-alpha"),
            ("作者", "YamaArashi"),
        ]
        for i, (label, value) in enumerate(lines):
            ctk.CTkLabel(info_frame, text=f"{label}:", font=ctk.CTkFont(size=13, weight="bold"),
                         ).grid(row=i, column=0, sticky="e", padx=(0, 8), pady=2)
            ctk.CTkLabel(info_frame, text=value, font=ctk.CTkFont(size=13),
                         text_color=("gray50", "gray60"),
                          ).grid(row=i, column=1, sticky="w", pady=2)

    def _build_page_preview(self):
        """构建预览页面"""
        pv = self.page_preview
        pv.grid_rowconfigure(0, weight=0)
        pv.grid_rowconfigure(1, weight=1)
        pv.grid_columnconfigure(0, weight=1)
        pv.grid_columnconfigure(1, weight=1, uniform="preview")

        top = ctk.CTkFrame(pv, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.preview_file_label = ctk.CTkLabel(
            top, text="未选择文件", font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"))
        self.preview_file_label.pack(side="left", padx=(0, 8))

        ctk.CTkButton(top, text="选择文件", width=80,
                      command=self._select_preview_file).pack(side="left")

        self.preview_surface_label = ctk.CTkLabel(pv, text="表图效果（白底）",
                                                  text_color="gray50")
        self.preview_surface_label.grid(row=1, column=0, sticky="nsew", padx=(0, 3))
        self.preview_surface_label.bind("<Configure>",
                                        lambda e: self._refresh_preview_images())

        self.preview_inner_label = ctk.CTkLabel(pv, text="里图效果（黑底）",
                                                text_color="gray50")
        self.preview_inner_label.grid(row=1, column=1, sticky="nsew", padx=(3, 0))
        self.preview_inner_label.bind("<Configure>",
                                      lambda e: self._refresh_preview_images())

    def _select_preview_file(self):
        export = self.export_dir_var.get().strip()
        initial_dir = export if export and Path(export).exists() else str(Path.cwd())
        file_path = filedialog.askopenfilename(
            title="选择 PNG 文件预览",
            initialdir=initial_dir,
            filetypes=[("PNG 文件", "*.png"), ("所有文件", "*.*")],
        )
        if file_path:
            self._load_preview(file_path)

    def _load_preview(self, file_path: str):
        """加载 PNG 并生成白底/黑底预览"""
        try:
            img = Image.open(file_path).convert("RGBA")
            w, h = img.size
            self.preview_file_label.configure(text=Path(file_path).name)

            white_bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
            black_bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))

            self._preview_surface_img = Image.alpha_composite(white_bg, img)
            self._preview_inner_img = Image.alpha_composite(black_bg, img)

            self._refresh_preview_images()
        except Exception as e:
            messagebox.showerror("错误", f"无法加载预览: {e}")

    def _refresh_preview_images(self):
        if not getattr(self, "_preview_surface_img", None):
            return
        try:
            def _fit(img, label):
                lw = max(label.winfo_width(), 1)
                lh = max(label.winfo_height(), 1)
                lw = max(lw - 20, 50)
                lh = max(lh - 20, 50)
                preview = img.copy()
                preview.thumbnail((lw, lh), Image.NEAREST)
                return ImageTk.PhotoImage(preview)

            sp = _fit(self._preview_surface_img, self.preview_surface_label)
            ip = _fit(self._preview_inner_img, self.preview_inner_label)

            self.preview_surface_label.configure(image=sp, text="")
            self.preview_surface_label.image = sp
            self.preview_inner_label.configure(image=ip, text="")
            self.preview_inner_label.image = ip
        except Exception:
            pass

    # ==================== 预览区 ====================

    def _build_preview_area(self, pad: int):
        left_frame = self._section_frame(self.page_home,
                                         "表图 (缩略图 / 封面)", 0, 0, pad)
        right_frame = self._section_frame(self.page_home,
                                          "里图 (原图 / 点开后可见)", 0, 1, pad)

        self.surface_preview_label = ctk.CTkLabel(
            left_frame, text="", text_color="gray50",
        )
        self.surface_preview_label.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(4, 8))

        ctk.CTkButton(left_frame, text="选择表图", width=120,
                      command=self._select_surface).grid(row=2, column=0, pady=(0, pad))

        self.inner_preview_label = ctk.CTkLabel(
            right_frame, text="", text_color="gray50",
        )
        self.inner_preview_label.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(4, 8))

        ctk.CTkButton(right_frame, text="选择里图", width=120,
                      command=self._select_inner).grid(row=2, column=0, pady=(0, pad))

        self.surface_preview_label.bind("<Configure>",
                                        lambda e: self._refresh_surface_preview())
        self.inner_preview_label.bind("<Configure>",
                                      lambda e: self._refresh_inner_preview())

    def _section_frame(self, parent, title: str, row: int, col: int,
                        pad: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, corner_radius=10, border_width=1,
                             border_color=("gray75", "gray30"))
        margin = pad // 2
        frame.grid(row=row, column=col, sticky="nsew",
                   padx=(margin, margin), pady=(pad, pad // 2))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=0)
        ctk.CTkLabel(frame, text=title,
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=pad + 2, pady=(pad, 2))
        return frame

    # ==================== 设置区 ====================

    def _build_settings_area(self, pad: int):
        settings = ctk.CTkFrame(self.page_home, corner_radius=10, border_width=1,
                                border_color=("gray75", "gray30"))
        settings.grid(row=1, column=0, columnspan=2, sticky="ew",
                      padx=pad, pady=(0, pad))
        settings.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(settings, text="处理参数",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w",
            padx=pad + 2, pady=(pad, 4))

        row = 1
        ef = ctk.CTkFont(size=13)

        ctk.CTkLabel(settings, text="亮度增强 (表图)", font=ef).grid(
            row=row, column=0, sticky="w", padx=(pad + 6, pad), pady=6)
        self.slider_enhance = ctk.CTkSlider(
            settings, from_=0, to=100, number_of_steps=10,
            command=lambda v: self._on_enhance_change(v),
        )
        self.slider_enhance.grid(row=row, column=1, sticky="ew", padx=(0, pad), pady=6)
        self.brightness_enhance_label = ctk.CTkLabel(
            settings, text="50", width=36, anchor="e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.brightness_enhance_label.grid(row=row, column=2, padx=(0, pad + 4))
        row += 1

        ctk.CTkLabel(settings, text="亮度削减 (里图)", font=ef).grid(
            row=row, column=0, sticky="w", padx=(pad + 6, pad), pady=6)
        self.slider_reduce = ctk.CTkSlider(
            settings, from_=-100, to=0, number_of_steps=10,
            command=lambda v: self._on_reduce_change(v),
        )
        self.slider_reduce.grid(row=row, column=1, sticky="ew", padx=(0, pad), pady=6)
        self.brightness_reduce_label = ctk.CTkLabel(
            settings, text="-50", width=36, anchor="e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.brightness_reduce_label.grid(row=row, column=2, padx=(0, pad + 4))
        row += 1

        sep = ctk.CTkFrame(settings, height=2, fg_color=("gray75", "gray35"))
        sep.grid(row=row, column=0, columnspan=3, sticky="ew",
                 padx=pad + 4, pady=(8, 4))
        row += 1

        ctk.CTkLabel(settings, text="导出目录", font=ef).grid(
            row=row, column=0, sticky="w", padx=(pad + 6, pad), pady=8)
        self.export_dir_var = StringVar()
        ctk.CTkEntry(settings, textvariable=self.export_dir_var, font=ef,
                     corner_radius=6).grid(row=row, column=1, sticky="ew",
                                           padx=(0, pad), pady=8)
        ctk.CTkButton(settings, text="浏览", width=60,
                      command=self._browse_export_dir).grid(
            row=row, column=2, padx=(0, pad + 4), pady=8)

    # ==================== 底部栏 ====================

    def _build_bottom_bar(self, pad: int):
        bar = ctk.CTkFrame(self.page_home, corner_radius=10, border_width=1,
                           border_color=("gray75", "gray30"))
        bar.grid(row=2, column=0, columnspan=2, sticky="ew",
                 padx=pad, pady=(0, pad))
        bar.grid_columnconfigure(0, weight=0)
        bar.grid_columnconfigure(1, weight=0)
        bar.grid_columnconfigure(2, weight=1)

        self.btn_process = ctk.CTkButton(bar, text="开始合成", width=100,
                                         command=self._start_process)
        self.btn_process.grid(row=0, column=0, padx=(pad, 4), pady=pad)

        self.btn_open_folder = ctk.CTkButton(
            bar, text="打开保存目录", width=100,
            command=self._open_save_folder, state="disabled")
        self.btn_open_folder.grid(row=0, column=1, padx=4, pady=pad)

        self.progress_bar = ctk.CTkProgressBar(bar, height=12)
        self.progress_bar.grid(row=0, column=2, sticky="ew",
                               padx=(16, pad), pady=pad)
        self.progress_bar.set(0)

        self.status_var = StringVar(value="就绪")
        ctk.CTkLabel(bar, textvariable=self.status_var, anchor="w",
                     text_color=("gray50", "gray60")).grid(
            row=1, column=0, columnspan=3, sticky="ew",
            padx=pad + 4, pady=(0, pad))

    # ==================== 主题 ====================

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        target = "dark" if current == "Light" else "light"
        ctk.set_appearance_mode(target)
        self._refresh_icons()

    # ==================== 事件处理 ====================

    def _on_enhance_change(self, value):
        self.brightness_enhance_label.configure(text=str(int(round(value))))

    def _on_reduce_change(self, value):
        self.brightness_reduce_label.configure(text=str(int(round(value))))

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
                surface=self.surface_image, inner=self.inner_image,
                brightness_enhancement=enh, brightness_reduction=red,
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
        self.btn_process.configure(state="disabled" if processing else "normal")

    def _open_save_folder(self):
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
        if self.config.export_directory:
            self.btn_open_folder.configure(state="normal")
        self._on_enhance_change(self.slider_enhance.get())
        self._on_reduce_change(self.slider_reduce.get())

    def _save_config_from_ui(self):
        self.config.brightness_enhancement = float(self.slider_enhance.get())
        self.config.brightness_reduction = float(self.slider_reduce.get())
        self.config.export_directory = self.export_dir_var.get().strip()
        self.config.save()
        self.logger.debug("配置已保存")

    # ==================== 启动 ====================

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())
        self.root.mainloop()
        self._cleanup_thumbnails()
