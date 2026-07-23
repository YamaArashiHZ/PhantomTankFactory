use std::path::{Path, PathBuf};

use chrono::Local;
use image::{ImageReader, RgbaImage};

use super::ops;

#[derive(Debug, thiserror::Error)]
pub enum ProcessError {
    #[error("无法打开图片: {0}")]
    Open(String),
    #[error("无法解码图片: {0}")]
    Decode(String),
    #[error("无法保存图片: {0}")]
    Save(String),
    #[error("无法创建目录: {0}")]
    CreateDir(String),
}

fn load_rgba(path: &Path) -> Result<RgbaImage, ProcessError> {
    let reader = ImageReader::open(path)
        .map_err(|e| ProcessError::Open(format!("{} ({e})", path.display())))?
        .with_guessed_format()
        .map_err(|e| ProcessError::Open(format!("{} ({e})", path.display())))?;
    let img = reader
        .decode()
        .map_err(|e| ProcessError::Decode(format!("{} ({e})", path.display())))?;
    Ok(img.to_rgba8())
}

/// 完整幻影坦克合成流水线，返回输出 PNG 路径。
pub fn process_phantom_tank(
    surface_path: &Path,
    inner_path: &Path,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    output_dir: &Path,
) -> Result<PathBuf, ProcessError> {
    let surface = load_rgba(surface_path)?;
    let inner = load_rgba(inner_path)?;

    let (surface, inner) = ops::resize_and_pad(&surface, &inner);
    let gray_surface = ops::grayscale_keep_alpha(&surface);
    let gray_inner = ops::grayscale_keep_alpha(&inner);

    let bright_surface = ops::adjust_brightness(&gray_surface, brightness_enhancement);
    let bright_inner = ops::adjust_brightness(&gray_inner, brightness_reduction);

    let inverted_surface = ops::invert_keep_alpha(&bright_surface);
    let dodged = ops::linear_dodge(&inverted_surface, &bright_inner);
    let divided = ops::divide(&bright_inner, &dodged);
    let result = ops::apply_red_as_alpha(&dodged, &divided);

    std::fs::create_dir_all(output_dir)
        .map_err(|e| ProcessError::CreateDir(format!("{} ({e})", output_dir.display())))?;

    let filename = format!("PhantomTank_{}.png", Local::now().format("%y%m%d_%H%M%S"));
    let save_path = output_dir.join(filename);
    result
        .save(&save_path)
        .map_err(|e| ProcessError::Save(format!("{} ({e})", save_path.display())))?;

    Ok(save_path)
}
