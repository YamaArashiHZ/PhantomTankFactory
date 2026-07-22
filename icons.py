"""
导航栏图标加载模块
从 assets/icons/ 读取 SVG 文件，使用 cairosvg 转换为 PIL Image

命名规则: {name}_{theme}.svg  (theme: light / dark)
"""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
from PIL import Image

ICON_SIZE = 24
ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def _svg_to_pil(svg_path: Path, size: int = ICON_SIZE) -> Image.Image:
    """将 SVG 文件渲染为 RGBA PIL Image"""
    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=size,
        output_height=size,
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def get_icons(light: bool) -> dict[str, Image.Image]:
    """返回当前主题下的三枚图标"""
    theme = "light" if light else "dark"
    names = ["home", "theme", "about"]
    result = {}
    for name in names:
        path = ICONS_DIR / f"{name}_{theme}.svg"
        if path.exists():
            result[name] = _svg_to_pil(path)
    return result
