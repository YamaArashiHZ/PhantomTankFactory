use image::{imageops, Rgba, RgbaImage};

/// 将里图按表图宽度等比缩放，并以较大宽高为画布居中透明填充。
pub fn resize_and_pad(surface: &RgbaImage, inner: &RgbaImage) -> (RgbaImage, RgbaImage) {
    let (sw, sh) = surface.dimensions();
    let (iw, ih) = inner.dimensions();

    let ratio = sw as f64 / iw as f64;
    let new_iw = ((iw as f64) * ratio).round().max(1.0) as u32;
    let new_ih = ((ih as f64) * ratio).round().max(1.0) as u32;
    let resized_inner = imageops::resize(inner, new_iw, new_ih, imageops::FilterType::Lanczos3);

    let max_w = sw.max(new_iw);
    let max_h = sh.max(new_ih);

    let surface_out = if sw < max_w || sh < max_h {
        let mut canvas = RgbaImage::from_pixel(max_w, max_h, Rgba([0, 0, 0, 0]));
        let ox = (max_w - sw) / 2;
        let oy = (max_h - sh) / 2;
        imageops::overlay(&mut canvas, surface, ox as i64, oy as i64);
        canvas
    } else {
        surface.clone()
    };

    let inner_out = if new_iw < max_w || new_ih < max_h {
        let mut canvas = RgbaImage::from_pixel(max_w, max_h, Rgba([0, 0, 0, 0]));
        let ox = (max_w - new_iw) / 2;
        let oy = (max_h - new_ih) / 2;
        imageops::overlay(&mut canvas, &resized_inner, ox as i64, oy as i64);
        canvas
    } else {
        resized_inner
    };

    (surface_out, inner_out)
}

/// 转灰度并保留 Alpha（输出仍为 RGBA，RGB 三通道相同）。
pub fn grayscale_keep_alpha(image: &RgbaImage) -> RgbaImage {
    let (w, h) = image.dimensions();
    let mut out = RgbaImage::new(w, h);
    for (x, y, px) in image.enumerate_pixels() {
        let g = ((u32::from(px[0]) * 299 + u32::from(px[1]) * 587 + u32::from(px[2]) * 114) / 1000)
            as u8;
        out.put_pixel(x, y, Rgba([g, g, g, px[3]]));
    }
    out
}

/// 亮度调整：>0 向白靠拢；<=0 各通道减半（与参考实现一致）。
pub fn adjust_brightness(image: &RgbaImage, lightness: f64) -> RgbaImage {
    let (w, h) = image.dimensions();
    let mut out = RgbaImage::new(w, h);

    if lightness > 0.0 {
        let factor = lightness / 100.0;
        for (x, y, px) in image.enumerate_pixels() {
            let r = (((f64::from(px[0]) + 255.0) * factor).round() as u32).min(255) as u8;
            let g = (((f64::from(px[1]) + 255.0) * factor).round() as u32).min(255) as u8;
            let b = (((f64::from(px[2]) + 255.0) * factor).round() as u32).min(255) as u8;
            out.put_pixel(x, y, Rgba([r, g, b, px[3]]));
        }
    } else {
        for (x, y, px) in image.enumerate_pixels() {
            out.put_pixel(x, y, Rgba([px[0] / 2, px[1] / 2, px[2] / 2, px[3]]));
        }
    }
    out
}

pub fn invert_keep_alpha(image: &RgbaImage) -> RgbaImage {
    let (w, h) = image.dimensions();
    let mut out = RgbaImage::new(w, h);
    for (x, y, px) in image.enumerate_pixels() {
        out.put_pixel(x, y, Rgba([255 - px[0], 255 - px[1], 255 - px[2], px[3]]));
    }
    out
}

/// 线性减淡：min(A + B, 255)，Alpha 置 255。
pub fn linear_dodge(a: &RgbaImage, b: &RgbaImage) -> RgbaImage {
    let (w, h) = a.dimensions();
    let mut out = RgbaImage::new(w, h);
    for y in 0..h {
        for x in 0..w {
            let pa = a.get_pixel(x, y);
            let pb = b.get_pixel(x, y);
            out.put_pixel(
                x,
                y,
                Rgba([
                    pa[0].saturating_add(pb[0]),
                    pa[1].saturating_add(pb[1]),
                    pa[2].saturating_add(pb[2]),
                    255,
                ]),
            );
        }
    }
    out
}

/// 划分：min(A * 255 / B, 255)，B 为 0 时按 1；Alpha 取 A。
pub fn divide(a: &RgbaImage, b: &RgbaImage) -> RgbaImage {
    let (w, h) = a.dimensions();
    let mut out = RgbaImage::new(w, h);
    for y in 0..h {
        for x in 0..w {
            let pa = a.get_pixel(x, y);
            let pb = b.get_pixel(x, y);
            let div = |base: u8, blend: u8| -> u8 {
                let d = if blend == 0 { 1u16 } else { u16::from(blend) };
                ((u16::from(base) * 255) / d).min(255) as u8
            };
            out.put_pixel(
                x,
                y,
                Rgba([
                    div(pa[0], pb[0]),
                    div(pa[1], pb[1]),
                    div(pa[2], pb[2]),
                    pa[3],
                ]),
            );
        }
    }
    out
}

/// 用 mask 的 R 通道作为 target 的 Alpha。
pub fn apply_red_as_alpha(mask: &RgbaImage, target: &RgbaImage) -> RgbaImage {
    let (w, h) = target.dimensions();
    let mut out = RgbaImage::new(w, h);
    for y in 0..h {
        for x in 0..w {
            let t = target.get_pixel(x, y);
            let m = mask.get_pixel(x, y);
            out.put_pixel(x, y, Rgba([t[0], t[1], t[2], m[0]]));
        }
    }
    out
}
