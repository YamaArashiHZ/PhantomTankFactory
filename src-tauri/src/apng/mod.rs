//! APNG 动图合成：表图作首帧，后续依次为多张里图，输出可循环的 APNG。

use std::io::Cursor;
use std::path::{Path, PathBuf};

use base64::{engine::general_purpose::STANDARD, Engine};
use image::{imageops, ImageReader, Rgba, RgbaImage};
use serde::Serialize;

pub mod encoder;

use encoder::{encode_apng, ApngOpts};

/// APNG 合成参数。
#[derive(Debug, Clone)]
pub struct ApngParams {
    /// 表图（首帧）显示时长（ms）。
    pub surface_delay_ms: u32,
    /// 每张里图显示时长（ms），长度应与里图数量一致。
    pub inner_delays_ms: Vec<u32>,
    /// 播放次数；0 = 无限循环。
    pub num_plays: u32,
    /// 压缩等级 0-9。
    pub compression: u8,
    /// 是否灰度量化。
    pub grayscale: bool,
    /// 成品大小上限（KB）；None 表示不限制。
    pub max_size_kb: Option<u64>,
}

/// APNG 处理结果。
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApngResult {
    pub output_path: String,
    /// 成品大小（KB，四舍五入）。
    pub size_kb: u64,
    /// 若存在提示（如未达上限），非空。
    pub warning: Option<String>,
}

/// 预览结果：每帧图片 + 每帧显示时长（ms）。
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApngPreview {
    pub frames: Vec<String>,
    pub delays_ms: Vec<u32>,
}

/// 加载图片为 RGBA。
fn load_rgba(path: &Path) -> Result<RgbaImage, String> {
    let reader = ImageReader::open(path).map_err(|e| format!("打开失败: {e}"))?;
    let img = reader
        .with_guessed_format()
        .map_err(|e| e.to_string())?
        .decode()
        .map_err(|e| format!("解码失败: {e}"))?
        .to_rgba8();
    Ok(img)
}

/// 将图片按最大边缩小（保持比例）。
fn downscale_to_edge(img: &RgbaImage, max_edge: u32) -> RgbaImage {
    let (w, h) = img.dimensions();
    let edge = w.max(h);
    if edge <= max_edge {
        return img.clone();
    }
    let scale = max_edge as f64 / edge as f64;
    let nw = ((w as f64) * scale).round().max(1.0) as u32;
    let nh = ((h as f64) * scale).round().max(1.0) as u32;
    imageops::resize(img, nw, nh, imageops::FilterType::Lanczos3)
}

/// 等比缩放并居中铺到目标画布（透明填充，contain）。
fn fit_to_canvas(img: &RgbaImage, w: u32, h: u32) -> RgbaImage {
    let (iw, ih) = img.dimensions();
    if iw == w && ih == h {
        return img.clone();
    }
    if w == 0 || h == 0 {
        return img.clone();
    }
    let scale = (w as f64 / iw as f64).min(h as f64 / ih as f64);
    let nw = ((iw as f64) * scale).round().max(1.0) as u32;
    let nh = ((ih as f64) * scale).round().max(1.0) as u32;
    let resized = imageops::resize(img, nw, nh, imageops::FilterType::Lanczos3);
    let mut canvas = RgbaImage::from_pixel(w, h, Rgba([0, 0, 0, 0]));
    let ox = ((w - nw) / 2) as i64;
    let oy = ((h - nh) / 2) as i64;
    imageops::overlay(&mut canvas, &resized, ox, oy);
    canvas
}

/// 当前可选收敛档位（先压后量化：优先降分辨率，再量化，再提高压缩）。
const SCALES: [f64; 6] = [1.0, 0.85, 0.7, 0.55, 0.42, 0.32];

/// 归一化一组帧到目标画布。
fn normalize_frames(frames: &[RgbaImage], cw: u32, ch: u32) -> Vec<RgbaImage> {
    let edge = cw.max(ch);
    frames
        .iter()
        .map(|f| {
            let d = downscale_to_edge(f, edge);
            fit_to_canvas(&d, cw, ch)
        })
        .collect()
}

/// 组装每帧时长（首帧=表图，其后依次为里图）。
fn delays_for_keep(params: &ApngParams, keep: usize) -> Vec<u32> {
    let mut d = vec![params.surface_delay_ms];
    d.extend_from_slice(&params.inner_delays_ms);
    d.truncate(keep);
    d
}

/// 尝试在「尺寸上限」内找到一组合适的编码。返回原始帧列表的请求 keep 数与编码字节。
fn converge(
    frames: &[RgbaImage],
    base_w: u32,
    base_h: u32,
    params: &ApngParams,
) -> (Vec<u8>, Option<String>) {
    let full = frames.len();
    // 可尝试保留的帧数（至少 2 帧，让步至多 2 帧）
    let mut keep_counts = vec![full];
    if full > 3 {
        keep_counts.push(full - 1);
        keep_counts.push(full - 2);
    } else if full > 2 {
        keep_counts.push(full - 1);
    }
    keep_counts.retain(|&k| k >= 2);
    // 降序：优先保留全部帧；无大小上限时第一次即返回全部帧
    keep_counts.sort_by(|a, b| b.cmp(a));
    keep_counts.dedup();

    let grayscale_opts: Vec<bool> = if params.grayscale {
        vec![true]
    } else {
        vec![false, true]
    };
    let comps: Vec<u8> = if params.compression >= 8 {
        vec![params.compression]
    } else {
        vec![params.compression, 9]
    };

    let cap_bytes = params.max_size_kb.map(|kb| kb.saturating_mul(1024));
    let mut best: Option<(Vec<u8>, u64)> = None; // (bytes, size)

    for &scale in SCALES.iter() {
        let cw = ((base_w as f64) * scale).round().max(16.0) as u32;
        let ch = ((base_h as f64) * scale).round().max(16.0) as u32;
        for &keep in keep_counts.iter() {
            let norm = normalize_frames(&frames[..keep], cw, ch);
            let delays = delays_for_keep(params, keep);
            for &gray in grayscale_opts.iter() {
                for &comp in comps.iter() {
                    let opts = ApngOpts {
                        width: cw,
                        height: ch,
                        num_plays: params.num_plays,
                        compression: comp,
                        grayscale: gray,
                        delays_ms: delays.clone(),
                    };
                    if let Ok(bytes) = encode_apng(&norm, &opts) {
                        let size = bytes.len() as u64;
                        if let Some(cap) = cap_bytes {
                            if size <= cap {
                                return (bytes, None);
                            }
                            if best.as_ref().is_none_or(|(_, s)| size < *s) {
                                best = Some((bytes, size));
                            }
                        } else {
                            return (bytes, None);
                        }
                    }
                }
            }
        }
    }

    // 达不到上限时，返回最小的一档并提示
    if let Some((bytes, size)) = best {
        let kb = (size + 512) / 1024;
        let cap = cap_bytes.map(|c| (c + 512) / 1024).unwrap_or(0);
        let msg =
            format!("已尽量小仍约 {kb} KB，未达到上限 {cap} KB；建议减少里图数量或降低分辨率");
        (bytes, Some(msg))
    } else {
        (Vec::new(), Some("编码失败".into()))
    }
}

/// 合成 APNG 并写入文件，返回输出路径、大小与可选提示。
pub fn process_apng(
    surface_path: &Path,
    inner_paths: &[PathBuf],
    params: &ApngParams,
    output_dir: &Path,
) -> Result<ApngResult, String> {
    let surface = load_rgba(surface_path)?;
    let (base_w, base_h) = surface.dimensions();
    let mut frames = vec![surface];
    for p in inner_paths {
        frames.push(load_rgba(p)?);
    }
    if frames.len() < 2 {
        return Err("至少需要 1 张表图和 1 张里图".into());
    }

    let (bytes, warning) = converge(&frames, base_w, base_h, params);

    std::fs::create_dir_all(output_dir).map_err(|e| format!("创建目录失败: {e}"))?;
    let name = format!(
        "PhantomTankAnim_{}.png",
        chrono::Local::now().format("%y%m%d_%H%M%S")
    );
    let save_path = output_dir.join(name);
    std::fs::write(&save_path, &bytes).map_err(|e| format!("写入失败: {e}"))?;

    let size_kb = (bytes.len() as u64 + 512) / 1024;
    Ok(ApngResult {
        output_path: save_path.to_string_lossy().into_owned(),
        size_kb,
        warning,
    })
}

/// 将单帧编码为 PNG data URL。
fn frame_data_url(img: &RgbaImage) -> Result<String, String> {
    let mut buf = Vec::new();
    img.write_to(&mut Cursor::new(&mut buf), image::ImageFormat::Png)
        .map_err(|e| e.to_string())?;
    Ok(format!("data:image/png;base64,{}", STANDARD.encode(&buf)))
}

/// 生成预览：返回每帧 PNG data URL 与每帧显示时长（ms），供前端逐帧播放。
pub fn preview_apng(
    surface_path: &Path,
    inner_paths: &[PathBuf],
    params: &ApngParams,
    max_edge: u32,
) -> Result<ApngPreview, String> {
    let surface = load_rgba(surface_path)?;
    let (base_w, base_h) = surface.dimensions();
    let mut frames = vec![surface];
    for p in inner_paths {
        frames.push(load_rgba(p)?);
    }
    if frames.len() < 2 {
        return Err("至少需要 1 张表图和 1 张里图".into());
    }

    let base_edge = base_w.max(base_h);
    let preview_edge = if max_edge == 0 {
        base_edge
    } else {
        max_edge.min(base_edge)
    };
    let scale = preview_edge as f64 / base_edge as f64;
    let cw = ((base_w as f64) * scale).round().max(16.0) as u32;
    let ch = ((base_h as f64) * scale).round().max(16.0) as u32;
    let norm = normalize_frames(&frames, cw, ch);

    let mut urls = Vec::with_capacity(norm.len());
    for f in &norm {
        let img = if params.grayscale {
            crate::phantom::ops::grayscale_keep_alpha(f)
        } else {
            f.clone()
        };
        urls.push(frame_data_url(&img)?);
    }

    let delays_ms = delays_for_keep(params, frames.len());
    Ok(ApngPreview {
        frames: urls,
        delays_ms,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn solid(w: u32, h: u32, r: u8, g: u8, b: u8, a: u8) -> RgbaImage {
        RgbaImage::from_pixel(w, h, Rgba([r, g, b, a]))
    }

    /// 确定性噪声图（用于构造「不可压缩」的图，检验大小上限的收敛提示）。
    fn noise(w: u32, h: u32) -> RgbaImage {
        let mut img = RgbaImage::new(w, h);
        let mut x: u32 = 123456789;
        for (_, _, p) in img.enumerate_pixels_mut() {
            x = x.wrapping_mul(1103515245).wrapping_add(12345);
            let v = (x >> 16) as u8;
            *p = Rgba([v, v.wrapping_mul(3), v ^ 0x5a, 255]);
        }
        img
    }

    #[test]
    fn fit_same_canvas_unchanged() {
        let img = solid(4, 4, 10, 20, 30, 255);
        assert_eq!(fit_to_canvas(&img, 4, 4).dimensions(), (4, 4));
    }

    #[test]
    fn fit_contain_forces_canvas() {
        // 横图 8x2 铺到 4x4 画布：等比缩放为 4x1，垂直居中（占 y=1 一行）
        let img = solid(8, 2, 0, 0, 0, 255);
        let out = fit_to_canvas(&img, 4, 4);
        assert_eq!(out.dimensions(), (4, 4));
        assert_eq!(out.get_pixel(2, 1)[3], 255, "中心行应不透明");
        assert_eq!(out.get_pixel(0, 0)[3], 0, "上边角应透明");
        assert_eq!(out.get_pixel(1, 2)[3], 0, "下边角应透明");
    }

    #[test]
    fn downscale_to_edge_caps_edge() {
        let img = solid(800, 600, 0, 0, 0, 255);
        let out = downscale_to_edge(&img, 320);
        let (w, h) = out.dimensions();
        assert!(w.max(h) <= 320);
    }

    #[test]
    fn delays_keep_first_surface() {
        let params = ApngParams {
            surface_delay_ms: 1000,
            inner_delays_ms: vec![500, 700],
            num_plays: 0,
            compression: 6,
            grayscale: false,
            max_size_kb: None,
        };
        assert_eq!(delays_for_keep(&params, 3), vec![1000, 500, 700]);
        assert_eq!(delays_for_keep(&params, 1), vec![1000]);
    }

    #[test]
    fn converge_without_cap_returns_first() {
        let frames = vec![solid(8, 8, 255, 0, 0, 255), solid(8, 8, 0, 255, 0, 255)];
        let params = ApngParams {
            surface_delay_ms: 100,
            inner_delays_ms: vec![100],
            num_plays: 0,
            compression: 6,
            grayscale: false,
            max_size_kb: None,
        };
        let (bytes, warning) = converge(&frames, 8, 8, &params);
        assert!(!bytes.is_empty());
        assert!(warning.is_none());
    }

    /// 解析 APNG 的 acTL 帧数。
    fn actl_frame_count(bytes: &[u8]) -> Option<u32> {
        let mut off = 8usize;
        while off + 12 <= bytes.len() {
            let len =
                u32::from_be_bytes([bytes[off], bytes[off + 1], bytes[off + 2], bytes[off + 3]])
                    as usize;
            let ty = &bytes[off + 4..off + 8];
            if ty == b"acTL" {
                let nf = u32::from_be_bytes([
                    bytes[off + 8],
                    bytes[off + 9],
                    bytes[off + 10],
                    bytes[off + 11],
                ]);
                return Some(nf);
            }
            off += 12 + len;
            if ty == b"IEND" {
                break;
            }
        }
        None
    }

    #[test]
    fn converge_without_cap_keeps_all_frames() {
        // 4 帧、无上限：应保留全部 4 帧（回归：升序曾导致只保留 2 帧）
        let frames = vec![
            solid(8, 8, 255, 0, 0, 255),
            solid(8, 8, 0, 255, 0, 255),
            solid(8, 8, 0, 0, 255, 255),
            solid(8, 8, 255, 255, 0, 255),
        ];
        let params = ApngParams {
            surface_delay_ms: 100,
            inner_delays_ms: vec![100, 100, 100],
            num_plays: 0,
            compression: 6,
            grayscale: false,
            max_size_kb: None,
        };
        let (bytes, warning) = converge(&frames, 8, 8, &params);
        assert!(!bytes.is_empty());
        assert!(warning.is_none());
        assert_eq!(actl_frame_count(&bytes), Some(4));
    }

    #[test]
    fn converge_with_tiny_cap_returns_something() {
        // 用噪声图保证 1KB 上限无法达成，收敛应返回最小一档并给出提示
        let frames = vec![noise(400, 400), noise(400, 400)];
        let params = ApngParams {
            surface_delay_ms: 100,
            inner_delays_ms: vec![100],
            num_plays: 0,
            compression: 0,
            grayscale: true,
            max_size_kb: Some(1), // 1KB 太小
        };
        let (bytes, warning) = converge(&frames, 400, 400, &params);
        assert!(!bytes.is_empty());
        assert!(warning.is_some(), "未达上限时应有提示");
    }
}
