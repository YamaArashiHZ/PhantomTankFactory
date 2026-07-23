use std::collections::HashMap;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::sync::{LazyLock, Mutex};
use std::time::SystemTime;

use base64::{engine::general_purpose::STANDARD, Engine};
use chrono::Local;
use image::{imageops, ImageFormat, ImageReader, Rgba, RgbaImage};

use super::ops;

// ==================== 错误类型 ====================

#[derive(Debug, thiserror::Error)]
pub enum ProcessError {
    #[error("文件不存在: {0}")]
    NotFound(String),
    #[error("没有访问权限: {0}")]
    Permission(String),
    #[error("无法打开图片: {0}")]
    Open(String),
    #[error("无法解码图片（文件可能损坏或格式不支持）: {0}")]
    Decode(String),
    #[error("无法保存图片: {0}")]
    Save(String),
    #[error("无法创建目录: {0}")]
    CreateDir(String),
    #[error("无法编码预览: {0}")]
    Encode(String),
}

impl ProcessError {
    /// 按 IO 错误类型映射为更具体的错误。
    fn from_io(kind: std::io::ErrorKind, ctx: &str, path: &Path, err: &std::io::Error) -> Self {
        let detail = format!("{ctx}: {} ({err})", path.display());
        match kind {
            std::io::ErrorKind::NotFound => Self::NotFound(detail),
            std::io::ErrorKind::PermissionDenied => Self::Permission(detail),
            _ => Self::Open(detail),
        }
    }
}

// ==================== 解码缓存 ====================

/// 已解码图片缓存：路径 → (文件修改时间, RGBA)。
/// 预览拖动滑条时反复调用同一对图片，缓存可避免重复 IO + 解码。
static IMAGE_CACHE: LazyLock<Mutex<HashMap<PathBuf, (SystemTime, RgbaImage)>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// 缓存条数上限（表图 + 里图为主，留冗余）。
const CACHE_CAPACITY: usize = 4;

fn file_mtime(path: &Path) -> Option<SystemTime> {
    std::fs::metadata(path).ok()?.modified().ok()
}

fn load_rgba(path: &Path) -> Result<RgbaImage, ProcessError> {
    let canonical = std::fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf());
    let mtime = file_mtime(path);

    // 命中缓存（且文件未改动）则直接复用
    if let Some(mt) = mtime {
        if let Ok(cache) = IMAGE_CACHE.lock() {
            if let Some((cached_mtime, img)) = cache.get(&canonical) {
                if *cached_mtime == mt {
                    return Ok(img.clone());
                }
            }
        }
    }

    let reader = ImageReader::open(path)
        .map_err(|e| ProcessError::from_io(e.kind(), "打开", path, &e))?
        .with_guessed_format()
        .map_err(|e| ProcessError::from_io(e.kind(), "识别格式", path, &e))?;
    let img = reader
        .decode()
        .map_err(|e| ProcessError::Decode(format!("{} ({e})", path.display())))?
        .to_rgba8();

    // 写入缓存；超出容量时整体清空（场景简单，清重建代价低）
    if let (Some(mt), Ok(mut cache)) = (mtime, IMAGE_CACHE.lock()) {
        if cache.len() >= CACHE_CAPACITY {
            cache.clear();
        }
        cache.insert(canonical, (mt, img.clone()));
    }

    Ok(img)
}

// ==================== 图像处理 ====================

/// 最长边限制，保持比例（预览加速）。
fn downscale_max_edge(img: &RgbaImage, max_edge: u32) -> RgbaImage {
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

/// 合成幻影坦克 RGBA（不写盘）。
pub fn compose_phantom_tank(
    surface: &RgbaImage,
    inner: &RgbaImage,
    brightness_enhancement: f64,
    brightness_reduction: f64,
) -> RgbaImage {
    let (surface, inner) = ops::resize_and_pad(surface, inner);
    let gray_surface = ops::grayscale_keep_alpha(&surface);
    let gray_inner = ops::grayscale_keep_alpha(&inner);

    let bright_surface = ops::adjust_brightness(&gray_surface, brightness_enhancement);
    let bright_inner = ops::adjust_brightness(&gray_inner, brightness_reduction);

    let inverted_surface = ops::invert_keep_alpha(&bright_surface);
    let dodged = ops::linear_dodge(&inverted_surface, &bright_inner);
    let divided = ops::divide(&bright_inner, &dodged);
    ops::apply_red_as_alpha(&dodged, &divided)
}

/// 加载两图并合成幻影坦克 RGBA。
/// `max_edge`：`Some(edge)` 时先按最长边缩小（预览加速），`None` 使用原图。
fn compose_from_paths(
    surface_path: &Path,
    inner_path: &Path,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    max_edge: Option<u32>,
) -> Result<RgbaImage, ProcessError> {
    let surface_full = load_rgba(surface_path)?;
    let inner_full = load_rgba(inner_path)?;
    let (surface, inner) = match max_edge {
        Some(edge) => {
            let edge = edge.clamp(64, 8192);
            (
                downscale_max_edge(&surface_full, edge),
                downscale_max_edge(&inner_full, edge),
            )
        }
        None => (surface_full, inner_full),
    };
    Ok(compose_phantom_tank(
        &surface,
        &inner,
        brightness_enhancement,
        brightness_reduction,
    ))
}

/// 完整流水线，返回输出 PNG 路径。
pub fn process_phantom_tank(
    surface_path: &Path,
    inner_path: &Path,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    output_dir: &Path,
) -> Result<PathBuf, ProcessError> {
    let result = compose_from_paths(
        surface_path,
        inner_path,
        brightness_enhancement,
        brightness_reduction,
        None,
    )?;

    std::fs::create_dir_all(output_dir)
        .map_err(|e| ProcessError::CreateDir(format!("{} ({e})", output_dir.display())))?;

    let filename = format!("PhantomTank_{}.png", Local::now().format("%y%m%d_%H%M%S"));
    let save_path = output_dir.join(filename);
    result
        .save(&save_path)
        .map_err(|e| ProcessError::Save(format!("{} ({e})", save_path.display())))?;

    Ok(save_path)
}

fn alpha_on_solid(fg: &RgbaImage, r: u8, g: u8, b: u8) -> RgbaImage {
    let (w, h) = fg.dimensions();
    let mut out = RgbaImage::from_pixel(w, h, Rgba([r, g, b, 255]));
    imageops::overlay(&mut out, fg, 0, 0);
    out
}

fn rgba_to_data_url(img: &RgbaImage) -> Result<String, ProcessError> {
    let mut buf = Vec::new();
    {
        let mut cursor = Cursor::new(&mut buf);
        img.write_to(&mut cursor, ImageFormat::Png)
            .map_err(|e| ProcessError::Encode(e.to_string()))?;
    }
    Ok(format!("data:image/png;base64,{}", STANDARD.encode(buf)))
}

/// 实时预览：可选缩小后合成，白底=表图效果，黑底=里图效果。
/// `max_edge`：预览最长边；**0 表示原图不缩小**（如 320/640/1280/0）。
pub fn preview_phantom_tank(
    surface_path: &Path,
    inner_path: &Path,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    max_edge: u32,
) -> Result<(String, String), ProcessError> {
    let result = compose_from_paths(
        surface_path,
        inner_path,
        brightness_enhancement,
        brightness_reduction,
        if max_edge == 0 { None } else { Some(max_edge) },
    )?;

    let surface_fx = alpha_on_solid(&result, 255, 255, 255);
    let inner_fx = alpha_on_solid(&result, 0, 0, 0);

    Ok((rgba_to_data_url(&surface_fx)?, rgba_to_data_url(&inner_fx)?))
}
