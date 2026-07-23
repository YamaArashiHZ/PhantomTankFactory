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

/// 亮度调整：>0 向白色线性插值；<0 向黑色线性插值；=0 不变。
/// 与旧算法在 lightness=±50 时结果一致，但在其他值下提供平滑连续的变化。
pub fn adjust_brightness(image: &RgbaImage, lightness: f64) -> RgbaImage {
    let (w, h) = image.dimensions();
    let mut out = RgbaImage::new(w, h);

    if lightness >= 0.0 {
        let t = lightness / 100.0;
        for (x, y, px) in image.enumerate_pixels() {
            let blend = |c: u8| (f64::from(c) + t * (255.0 - f64::from(c))).round() as u8;
            out.put_pixel(x, y, Rgba([blend(px[0]), blend(px[1]), blend(px[2]), px[3]]));
        }
    } else {
        let factor = 1.0 + lightness / 100.0;
        for (x, y, px) in image.enumerate_pixels() {
            let dim = |c: u8| (f64::from(c) * factor).round() as u8;
            out.put_pixel(x, y, Rgba([dim(px[0]), dim(px[1]), dim(px[2]), px[3]]));
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

#[cfg(test)]
mod tests {
    use super::*;

    fn px(r: u8, g: u8, b: u8, a: u8) -> Rgba<u8> {
        Rgba([r, g, b, a])
    }

    fn img_2x2(pixels: [Rgba<u8>; 4]) -> RgbaImage {
        RgbaImage::from_fn(2, 2, |x, y| pixels[(y * 2 + x) as usize])
    }

    // ---------- resize_and_pad ----------

    #[test]
    fn resize_and_pad_same_size() {
        let s = RgbaImage::from_pixel(4, 4, px(255, 0, 0, 255));
        let i = RgbaImage::from_pixel(4, 4, px(0, 255, 0, 255));
        let (so, io) = resize_and_pad(&s, &i);
        assert_eq!(so.dimensions(), (4, 4));
        assert_eq!(io.dimensions(), (4, 4));
    }

    #[test]
    fn resize_and_pad_surface_wider() {
        let s = RgbaImage::from_pixel(6, 4, px(255, 0, 0, 255));
        let i = RgbaImage::from_pixel(2, 2, px(0, 255, 0, 255));
        let (so, io) = resize_and_pad(&s, &i);
        assert_eq!(so.dimensions(), (6, 6));
        assert_eq!(io.dimensions(), (6, 6));
    }

    #[test]
    fn resize_and_pad_inner_wider() {
        let s = RgbaImage::from_pixel(2, 2, px(255, 0, 0, 255));
        let i = RgbaImage::from_pixel(6, 4, px(0, 255, 0, 255));
        let (so, io) = resize_and_pad(&s, &i);
        assert_eq!(so.dimensions(), (2, 2));
        assert_eq!(io.dimensions(), (2, 2));
    }

    // ---------- grayscale_keep_alpha ----------

    #[test]
    fn grayscale_keeps_alpha() {
        let img = RgbaImage::from_pixel(1, 1, px(100, 150, 200, 128));
        let out = grayscale_keep_alpha(&img);
        let p = out.get_pixel(0, 0);
        let expected = ((100u32 * 299 + 150 * 587 + 200 * 114) / 1000) as u8;
        assert_eq!(p[0], expected);
        assert_eq!(p[1], expected);
        assert_eq!(p[2], expected);
        assert_eq!(p[3], 128);
    }

    #[test]
    fn grayscale_black_white() {
        let img = RgbaImage::from_pixel(1, 1, px(0, 0, 0, 255));
        let out = grayscale_keep_alpha(&img);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2]), (0, 0, 0));

        let img = RgbaImage::from_pixel(1, 1, px(255, 255, 255, 255));
        let out = grayscale_keep_alpha(&img);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2]), (255, 255, 255));
    }

    // ---------- adjust_brightness ----------

    #[test]
    fn brightness_positive_halfway() {
        let img = RgbaImage::from_pixel(1, 1, px(100, 0, 255, 200));
        let out = adjust_brightness(&img, 50.0);
        let p = out.get_pixel(0, 0);
        let blend = |c: u8| (f64::from(c) + 0.5 * (255.0 - f64::from(c))).round() as u8;
        assert_eq!(p[0], blend(100));
        assert_eq!(p[1], blend(0));
        assert_eq!(p[2], blend(255));
        assert_eq!(p[3], 200);
    }

    #[test]
    fn brightness_positive_quarter() {
        let img = RgbaImage::from_pixel(1, 1, px(100, 0, 200, 255));
        let out = adjust_brightness(&img, 25.0);
        let p = out.get_pixel(0, 0);
        let blend = |c: u8| (f64::from(c) + 0.25 * (255.0 - f64::from(c))).round() as u8;
        assert_eq!(p[0], blend(100));
        assert_eq!(p[1], blend(0));
        assert_eq!(p[2], blend(200));
    }

    #[test]
    fn brightness_negative_halfway() {
        let img = RgbaImage::from_pixel(1, 1, px(200, 100, 50, 77));
        let out = adjust_brightness(&img, -50.0);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (100, 50, 25, 77));
    }

    #[test]
    fn brightness_negative_quarter() {
        let img = RgbaImage::from_pixel(1, 1, px(200, 100, 50, 77));
        let out = adjust_brightness(&img, -25.0);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (150, 75, 38, 77));
    }

    #[test]
    fn brightness_zero_is_identity() {
        let img = RgbaImage::from_pixel(1, 1, px(200, 100, 50, 77));
        let out = adjust_brightness(&img, 0.0);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (200, 100, 50, 77));
    }

    #[test]
    fn brightness_max_is_white() {
        let img = RgbaImage::from_pixel(1, 1, px(50, 100, 150, 99));
        let out = adjust_brightness(&img, 100.0);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (255, 255, 255, 99));
    }

    #[test]
    fn brightness_min_is_black() {
        let img = RgbaImage::from_pixel(1, 1, px(50, 100, 150, 99));
        let out = adjust_brightness(&img, -100.0);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (0, 0, 0, 99));
    }

    // ---------- invert_keep_alpha ----------

    #[test]
    fn invert_preserves_alpha() {
        let img = RgbaImage::from_pixel(1, 1, px(30, 128, 255, 77));
        let out = invert_keep_alpha(&img);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (225, 127, 0, 77));
    }

    #[test]
    fn invert_twice_is_identity() {
        let img = RgbaImage::from_pixel(2, 2, px(50, 100, 150, 200));
        let out = invert_keep_alpha(&invert_keep_alpha(&img));
        for (x, y, p) in out.enumerate_pixels() {
            let o = img.get_pixel(x, y);
            assert_eq!((p[0], p[1], p[2], p[3]), (o[0], o[1], o[2], o[3]));
        }
    }

    // ---------- linear_dodge ----------

    #[test]
    fn linear_dodge_saturation() {
        let a = img_2x2([px(200, 100, 50, 255), px(0, 0, 0, 255), px(255, 0, 0, 255), px(10, 20, 30, 255)]);
        let b = img_2x2([px(100, 200, 50, 128), px(0, 0, 0, 255), px(0, 255, 0, 255), px(40, 30, 20, 128)]);
        let out = linear_dodge(&a, &b);
        assert_eq!((out.get_pixel(0, 0)[0], out.get_pixel(0, 0)[1], out.get_pixel(0, 0)[2], out.get_pixel(0, 0)[3]), (255, 255, 100, 255));
        assert_eq!((out.get_pixel(1, 0)[0], out.get_pixel(1, 0)[1], out.get_pixel(1, 0)[2], out.get_pixel(1, 0)[3]), (0, 0, 0, 255));
        assert_eq!((out.get_pixel(0, 1)[0], out.get_pixel(0, 1)[1], out.get_pixel(0, 1)[2], out.get_pixel(0, 1)[3]), (255, 255, 0, 255));
    }

    #[test]
    fn linear_dodge_alpha_always_255() {
        let a = RgbaImage::from_pixel(2, 2, px(0, 0, 0, 128));
        let b = RgbaImage::from_pixel(2, 2, px(0, 0, 0, 0));
        let out = linear_dodge(&a, &b);
        for (_, _, p) in out.enumerate_pixels() {
            assert_eq!(p[3], 255);
        }
    }

    // ---------- divide ----------

    #[test]
    fn divide_basic() {
        let a = img_2x2([px(128, 255, 0, 255), px(100, 0, 200, 255), px(50, 100, 150, 128), px(255, 128, 64, 255)]);
        let b = img_2x2([px(64, 128, 255, 128), px(0, 0, 0, 255), px(10, 20, 30, 64), px(128, 255, 64, 255)]);
        let out = divide(&a, &b);
        let d = |base: u8, blend: u8| ((base as u16 * 255) / if blend == 0 { 1 } else { blend as u16 }).min(255) as u8;
        assert_eq!((out.get_pixel(0, 0)[0], out.get_pixel(0, 0)[1], out.get_pixel(0, 0)[2], out.get_pixel(0, 0)[3]), (d(128, 64), d(255, 128), d(0, 255), 255));
        assert_eq!((out.get_pixel(0, 1)[0], out.get_pixel(0, 1)[1], out.get_pixel(0, 1)[2], out.get_pixel(0, 1)[3]), (d(50, 10), d(100, 20), d(150, 30), 128));
    }

    #[test]
    fn divide_zero_blend_treated_as_1() {
        let a = RgbaImage::from_pixel(1, 1, px(100, 200, 50, 255));
        let b = RgbaImage::from_pixel(1, 1, px(0, 0, 0, 255));
        let out = divide(&a, &b);
        let p = out.get_pixel(0, 0);
        assert_eq!(p[3], 255);
        assert_eq!((p[0], p[1], p[2]), (255, 255, 255));
    }

    // ---------- apply_red_as_alpha ----------

    #[test]
    fn apply_red_as_alpha_correct() {
        let mask = RgbaImage::from_pixel(1, 1, px(200, 100, 50, 128));
        let target = RgbaImage::from_pixel(1, 1, px(50, 100, 150, 255));
        let out = apply_red_as_alpha(&mask, &target);
        let p = out.get_pixel(0, 0);
        assert_eq!((p[0], p[1], p[2], p[3]), (50, 100, 150, 200));
    }
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
