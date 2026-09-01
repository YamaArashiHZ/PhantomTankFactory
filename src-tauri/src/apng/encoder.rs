//! APNG（Animated PNG）编码器。
//!
//! 基于 `png` crate（0.17）的动画支持：`acTL` 帧数/循环、每帧 `fcTL` 的
//! `delay_num/delay_den`，逐帧 `write_image_data`（首帧走 `IDAT`，后续帧 `fdAT`）。
//!
//! 支持：每帧独立时长（ms）、无限/固定次数循环、压缩等级（0-9）、灰度量化。

use image::RgbaImage;

/// APNG 编码选项。
#[derive(Debug, Clone)]
pub struct ApngOpts {
    /// 画布宽度（所有帧共享）。
    pub width: u32,
    /// 画布高度（所有帧共享）。
    pub height: u32,
    /// 播放次数；`0` 表示无限循环。
    pub num_plays: u32,
    /// 压缩等级 0-9；映射到 `png::Compression` 预设。
    pub compression: u8,
    /// 是否转灰度（量化，显著减小体积）。
    pub grayscale: bool,
    /// 每帧时长（毫秒），长度应与帧数一致；缺省取 `1000`。
    pub delays_ms: Vec<u32>,
}

/// 将 0-9 压缩等级映射到 `png::Compression` 预设。
fn compression_preset(level: u8) -> png::Compression {
    match level {
        0..=2 => png::Compression::Fast,
        3..=6 => png::Compression::Default,
        _ => png::Compression::Best,
    }
}

/// 毫秒转 PNG 帧延迟 `(delay_num, delay_den)`（秒 = num/den）。
fn delay_to_frac(ms: u32) -> (u16, u16) {
    let ms = ms.clamp(1, 65535);
    (ms as u16, 1000)
}

/// 灰度 + Alpha（2 通道）原始字节。
fn to_grayscale_alpha(frame: &RgbaImage) -> Vec<u8> {
    let (w, h) = frame.dimensions();
    let mut out = Vec::with_capacity((w * h * 2) as usize);
    for (_, _, p) in frame.enumerate_pixels() {
        let g =
            ((u32::from(p[0]) * 299 + u32::from(p[1]) * 587 + u32::from(p[2]) * 114) / 1000) as u8;
        out.push(g);
        out.push(p[3]);
    }
    out
}

/// 将一组同画布 RGBA 帧编码为 APNG 字节。
pub fn encode_apng(frames: &[RgbaImage], opts: &ApngOpts) -> Result<Vec<u8>, String> {
    if frames.is_empty() {
        return Err("至少需要 1 帧".into());
    }
    let mut out = Vec::new();
    {
        let mut enc = png::Encoder::new(&mut out, opts.width, opts.height);
        enc.set_color(if opts.grayscale {
            png::ColorType::GrayscaleAlpha
        } else {
            png::ColorType::Rgba
        });
        enc.set_depth(png::BitDepth::Eight);
        enc.set_compression(compression_preset(opts.compression));
        enc.set_animated(frames.len() as u32, opts.num_plays)
            .map_err(|e| e.to_string())?;

        let mut writer = enc.write_header().map_err(|e| e.to_string())?;
        for (i, frame) in frames.iter().enumerate() {
            let (num, den) = delay_to_frac(opts.delays_ms.get(i).copied().unwrap_or(1000));
            writer
                .set_frame_delay(num, den)
                .map_err(|e| e.to_string())?;
            if opts.grayscale {
                let data = to_grayscale_alpha(frame);
                writer.write_image_data(&data).map_err(|e| e.to_string())?;
            } else {
                writer
                    .write_image_data(frame.as_raw())
                    .map_err(|e| e.to_string())?;
            }
        }
        writer.finish().map_err(|e| e.to_string())?;
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use image::{Rgba, RgbaImage};

    fn solid(w: u32, h: u32, r: u8, g: u8, b: u8, a: u8) -> RgbaImage {
        RgbaImage::from_pixel(w, h, Rgba([r, g, b, a]))
    }

    fn frames() -> Vec<RgbaImage> {
        vec![solid(4, 4, 255, 0, 0, 255), solid(4, 4, 0, 255, 0, 255)]
    }

    /// 校验产出的字节是否为合法 APNG：签名、acTL、fcTL、fdAT、IEND。
    #[test]
    fn encode_produces_valid_apng_structure() {
        let opts = ApngOpts {
            width: 4,
            height: 4,
            num_plays: 0,
            compression: 6,
            grayscale: false,
            delays_ms: vec![1000, 500],
        };
        let bytes = encode_apng(&frames(), &opts).expect("encode");
        assert_eq!(&bytes[0..8], b"\x89PNG\r\n\x1a\n");

        let mut off = 8usize;
        let mut types = Vec::new();
        let mut actl = None;
        let mut fctl = 0;
        let mut fdat = 0;
        while off + 8 <= bytes.len() {
            let len =
                u32::from_be_bytes([bytes[off], bytes[off + 1], bytes[off + 2], bytes[off + 3]])
                    as usize;
            let ty = &bytes[off + 4..off + 8];
            let tstr = std::str::from_utf8(ty).unwrap();
            types.push(tstr.to_string());
            match tstr {
                "acTL" => {
                    let nframes = u32::from_be_bytes([
                        bytes[off + 8],
                        bytes[off + 9],
                        bytes[off + 10],
                        bytes[off + 11],
                    ]);
                    let nplays = u32::from_be_bytes([
                        bytes[off + 12],
                        bytes[off + 13],
                        bytes[off + 14],
                        bytes[off + 15],
                    ]);
                    actl = Some((nframes, nplays));
                }
                "fcTL" => fctl += 1,
                "fdAT" => fdat += 1,
                _ => {}
            }
            off += 12 + len;
            if tstr == "IEND" {
                break;            }
        }

        assert_eq!(actl, Some((2, 0)), "acTL 应为 2 帧、无限循环");
        assert_eq!(fctl, 2, "应为 2 个 fcTL（每帧一个）");
        assert_eq!(fdat, 1, "第二帧起应为 1 个 fdAT（首帧用 IDAT）");
        assert_eq!(types.last().map(String::as_str), Some("IEND"));
    }

    #[test]
    fn grayscale_produces_half_channels() {
        let frames = vec![solid(2, 2, 255, 0, 0, 255), solid(2, 2, 0, 255, 0, 255)];
        let opts = ApngOpts {
            width: 2,
            height: 2,
            num_plays: 1,
            compression: 6,
            grayscale: true,
            delays_ms: vec![300, 300],
        };
        let bytes = encode_apng(&frames, &opts).expect("encode grayscale");
        assert!(bytes.windows(4).any(|w| w == b"acTL"));
    }

    /// 解析 acTL 的 num_plays。
    fn actl_num_plays(bytes: &[u8]) -> Option<u32> {
        let mut off = 8usize;
        while off + 16 <= bytes.len() {
            let len =
                u32::from_be_bytes([bytes[off], bytes[off + 1], bytes[off + 2], bytes[off + 3]])
                    as usize;
            let ty = &bytes[off + 4..off + 8];
            if ty == b"acTL" {
                let n = u32::from_be_bytes([
                    bytes[off + 12],
                    bytes[off + 13],
                    bytes[off + 14],
                    bytes[off + 15],
                ]);
                return Some(n);
            }
            off += 12 + len;
            if ty == b"IEND" {
                break;
            }
        }
        None
    }

    #[test]
    fn encode_writes_num_plays() {
        let opts = ApngOpts {
            width: 4,
            height: 4,
            num_plays: 3,
            compression: 6,
            grayscale: false,
            delays_ms: vec![1000, 500],
        };
        let bytes = encode_apng(&frames(), &opts).expect("encode");
        assert_eq!(actl_num_plays(&bytes), Some(3));
    }
}
