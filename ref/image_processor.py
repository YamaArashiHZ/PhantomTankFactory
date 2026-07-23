"""
PhantomTank 图像处理模块
封装幻影坦克图片合成的完整流水线

处理流程：
    1. 尺寸对齐 ── 将表图与里图缩放至相同宽度，高度不足则填充透明像素
    2. 灰度转换 ── 保留 Alpha 通道的前提下将图像转为灰度
    3. 亮度调整 ── 表图提亮、里图压暗，使两张图的亮度拉开差距
    4. 图像反相 ── 将表图颜色反转（用于后续混合）
    5. 线性减淡 ── 表图(反相) + 里图，产生混合纹理
    6. 划分混合 ── 里图 / 线性减淡结果，分离信息通道
    7. 通道模板 ── 将线性减淡结果的红色通道用作透明度遮罩

详细原理参考：https://www.bilibili.com/read/cv11801542
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageOps


# ==================== 基础图像操作 ====================

def resize_and_pad(
    surface: Image.Image,
    inner: Image.Image,
) -> Tuple[Image.Image, Image.Image]:
    """
    对齐两张图片的尺寸：将里图横向缩放至与表图宽度相等，
    高度不足的一侧用透明像素填充补齐。

    Args:
        surface: 表图 (预览时可见)
        inner:   里图 (点开大图后可见)

    Returns:
        (resized_surface, resized_inner)
    """
    sw, sh = surface.size
    iw, ih = inner.size

    # 按表图宽度等比缩放里图
    ratio = sw / iw
    new_iw = int(ratio * iw)
    new_ih = int(ratio * ih)
    resized_inner = inner.resize((new_iw, new_ih), Image.LANCZOS)

    # 以较高者为准，在较矮图片上下加透明填充
    max_h = max(sh, new_ih)
    max_w = max(sw, new_iw)

    # 表图填充
    if sw < max_w or sh < max_h:
        canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        canvas.paste(surface, ((max_w - sw) // 2, (max_h - sh) // 2))
        surface = canvas

    # 里图填充
    if new_iw < max_w or new_ih < max_h:
        canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        canvas.paste(resized_inner, ((max_w - new_iw) // 2, (max_h - new_ih) // 2))
        resized_inner = canvas

    return surface, resized_inner


def grayscale_keep_alpha(image: Image.Image) -> Image.Image:
    """
    将 RGBA 图像转为灰度，同时保留原始 Alpha 通道。

    Args:
        image: 输入的 RGBA 图像

    Returns:
        LA 模式灰度图像 (L: 灰度, A: 原始透明度)
    """
    image = image.convert("RGBA")
    r, g, b, a = image.split()
    gray = Image.merge("RGB", (r, g, b)).convert("L")
    return Image.merge("LA", (gray, a))


def adjust_brightness(image: Image.Image, lightness: float) -> Image.Image:
    """
    调整 RGBA 图像的亮度。

    原理：
      - lightness > 0: 向白色靠拢  r' = (r + 255) * (lightness / 100)
      - lightness < 0: 向黑色靠拢  r' = r / 2

    Args:
        image:     RGBA 图像（通常为灰度 LA 转换而来）
        lightness: 亮度调整值，范围 [-100, 100]

    Returns:
        RGBA 模式调整后的图像
    """
    image = image.convert("RGBA")
    r, g, b, a = image.split()
    rgb = image.convert("RGB")

    pixels = list(rgb.getdata())
    adjusted = []

    if lightness > 0:
        factor = lightness / 100.0
        for pr, pg, pb in pixels:
            adjusted.append((
                min(255, int((pr + 255) * factor)),
                min(255, int((pg + 255) * factor)),
                min(255, int((pb + 255) * factor)),
            ))
    else:
        for pr, pg, pb in pixels:
            adjusted.append((pr // 2, pg // 2, pb // 2))

    bright = Image.new("RGB", rgb.size)
    bright.putdata(adjusted)

    # 重新拼回 Alpha 通道
    br, bg, bb = bright.split()
    return Image.merge("RGBA", (br, bg, bb, a))


def invert_image_keep_alpha(image: Image.Image) -> Image.Image:
    """
    反相 RGB 通道，保留原始 Alpha 通道。

    Args:
        image: RGBA 图像

    Returns:
        RGBA 反相图像
    """
    image = image.convert("RGBA")
    r, g, b, a = image.split()
    inverted = ImageOps.invert(image.convert("RGB"))
    ir, ig, ib = inverted.split()
    return Image.merge("RGBA", (ir, ig, ib, a))


# ==================== 混合模式 ====================

def linear_dodge(image_a: Image.Image, image_b: Image.Image) -> Image.Image:
    """
    线性减淡 (Linear Dodge / Add) 混合模式。

    公式: result = min(A + B, 255)
    - 白底上滴一滴黑墨，减淡后的效果是白色
    - 黑底上滴一滴白墨，减淡后的效果是白色

    Args:
        image_a, image_b: 两张 RGBA 图像，尺寸须一致

    Returns:
        RGBA 混合结果
    """
    image_a = image_a.convert("RGBA")
    image_b = image_b.convert("RGBA")

    w, h = image_a.size
    result = Image.new("RGBA", (w, h))

    pa = image_a.load()
    pb = image_b.load()
    pr = result.load()

    for y in range(h):
        for x in range(w):
            ra, ga, ba, _ = pa[x, y]
            rb, gb, bb, _ = pb[x, y]
            pr[x, y] = (
                min(ra + rb, 255),
                min(ga + gb, 255),
                min(ba + bb, 255),
            )

    return result


def divide(image_a: Image.Image, image_b: Image.Image) -> Image.Image:
    """
    划分 (Divide) 混合模式。

    公式: result = min(A * 255 / B, 255)，其中 B 为 0 时视作 1
    - 白底和黑画的交互：画一幅黑画在白纸上，划分后可见黑色
    - 黑底和白画的交互：画一幅白画在黑纸上，划分后可见白色

    Args:
        image_a: 基色层
        image_b: 混合色层

    Returns:
        RGBA 混合结果
    """
    image_a = image_a.convert("RGBA")
    image_b = image_b.convert("RGBA")

    w, h = image_a.size
    result = Image.new("RGBA", (w, h))

    pa = image_a.load()
    pb = image_b.load()
    pr = result.load()

    for y in range(h):
        for x in range(w):
            ra, ga, ba, aa = pa[x, y]
            rb, gb, bb, _ = pb[x, y]
            pr[x, y] = (
                min(255, ra * 255 // (rb if rb != 0 else 1)),
                min(255, ga * 255 // (gb if gb != 0 else 1)),
                min(255, ba * 255 // (bb if bb != 0 else 1)),
                aa,
            )

    return result


def apply_red_channel_as_alpha(
    mask_image: Image.Image,
    target_image: Image.Image,
) -> Image.Image:
    """
    将 mask 图像的红色通道值作为 target 图像的 Alpha 通道。

    Args:
        mask_image:   提供 R 通道作为透明度
        target_image: 待赋予透明度的图像

    Returns:
        RGBA 结果图像
    """
    mask_r = mask_image.convert("RGBA").split()[0]
    target = target_image.convert("RGBA")

    w, h = target.size
    result = Image.new("RGBA", (w, h))

    pt = target.load()
    pr = result.load()

    for y in range(h):
        for x in range(w):
            rt, gt, bt, _ = pt[x, y]
            alpha = mask_r.getpixel((x, y))
            pr[x, y] = (rt, gt, bt, alpha)

    return result


# ==================== 完整处理流水线 ====================

def process_phantom_tank(
    surface: Image.Image,
    inner: Image.Image,
    brightness_enhancement: float = 50.0,
    brightness_reduction: float = -50.0,
    output_path: str | Path = "",
    progress_callback=None,
) -> Path:
    """
    执行完整的幻影坦克合成流水线。

    Args:
        surface:                表图 (预览图)
        inner:                  里图 (点开后可见)
        brightness_enhancement: 表图亮度增强值 (0~100)
        brightness_reduction:   里图亮度削减值 (-100~0)
        output_path:            输出目录（空则使用当前目录）
        progress_callback:      进度回调函数 (step, total, description)

    Returns:
        输出文件路径
    """
    steps = [
        "尺寸对齐",
        "灰度转换",
        "亮度调整",
        "图像反相",
        "线性减淡",
        "划分混合",
        "通道模板",
        "保存图片",
    ]
    total = len(steps)

    def _progress(idx: int):
        """触发进度回调"""
        if progress_callback:
            progress_callback(idx + 1, total, steps[idx])

    # 1. 尺寸对齐
    _progress(0)
    surface, inner = resize_and_pad(surface, inner)

    # 2. 灰度转换
    _progress(1)
    gray_surface = grayscale_keep_alpha(surface)
    gray_inner = grayscale_keep_alpha(inner)

    # 3. 亮度调整
    _progress(2)
    bright_surface = adjust_brightness(gray_surface.convert("RGBA"), brightness_enhancement)
    bright_inner = adjust_brightness(gray_inner.convert("RGBA"), brightness_reduction)

    # 4. 图像反相（仅表图）
    _progress(3)
    inverted_surface = invert_image_keep_alpha(bright_surface)

    # 5. 线性减淡
    _progress(4)
    dodged = linear_dodge(inverted_surface, bright_inner)

    # 6. 划分混合
    _progress(5)
    divided = divide(bright_inner, dodged)

    # 7. 通道模板
    _progress(6)
    result = apply_red_channel_as_alpha(dodged, divided)

    # 8. 保存
    _progress(7)
    output_dir = Path(output_path) if output_path else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = "PhantomTank" + time.strftime("_%y%m%d_%H%M%S", time.localtime()) + ".png"
    save_path = output_dir / filename
    result.save(str(save_path))

    return save_path
