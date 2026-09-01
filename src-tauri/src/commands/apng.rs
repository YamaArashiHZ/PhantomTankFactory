//! APNG 合成/预览的 Tauri 命令。

use std::path::PathBuf;

use crate::apng::ApngParams;
use crate::commands::paths::resolve_temp_dir;

fn validate_and_params(
    _surface_path: &str,
    surface_delay_ms: u32,
    inner_paths: &[String],
    inner_delays_ms: &[u32],
    loop_plays: u32,
    compression: u8,
    grayscale: bool,
) -> Result<ApngParams, String> {
    if inner_paths.len() != inner_delays_ms.len() {
        return Err("里图时长与里图数量不一致".into());
    }
    if compression > 9 {
        return Err("压缩等级须在 0~9".into());
    }
    if surface_delay_ms == 0 || inner_delays_ms.contains(&0) {
        return Err("显示时长须大于 0".into());
    }
    Ok(ApngParams {
        surface_delay_ms,
        inner_delays_ms: inner_delays_ms.to_vec(),
        num_plays: loop_plays,
        compression,
        grayscale,
        max_size_kb: None,
    })
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub async fn process_apng(
    app: tauri::AppHandle,
    surface_path: String,
    surface_delay_ms: u32,
    inner_paths: Vec<String>,
    inner_delays_ms: Vec<u32>,
    loop_plays: u32,
    compression: u8,
    grayscale: bool,
    max_size_kb: Option<u32>,
    export_directory: String,
) -> Result<crate::apng::ApngResult, String> {
    let surface = PathBuf::from(&surface_path);
    if !surface.is_file() {
        return Err(format!("表图不存在: {surface_path}"));
    }
    let inner_paths_buf: Vec<PathBuf> = inner_paths.iter().map(PathBuf::from).collect();
    for p in &inner_paths_buf {
        if !p.is_file() {
            return Err(format!("里图不存在: {}", p.display()));
        }
    }

    let mut params = validate_and_params(
        &surface_path,
        surface_delay_ms,
        &inner_paths,
        &inner_delays_ms,
        loop_plays,
        compression,
        grayscale,
    )?;
    params.max_size_kb = max_size_kb.map(|v| v as u64);

    let output_dir = if export_directory.trim().is_empty() {
        resolve_temp_dir(&app)?
    } else {
        PathBuf::from(export_directory.trim())
    };

    let res = tauri::async_runtime::spawn_blocking(move || {
        crate::apng::process_apng(&surface, &inner_paths_buf, &params, &output_dir)
    })
    .await
    .map_err(|e| e.to_string())??;

    Ok(res)
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub async fn preview_apng(
    surface_path: String,
    surface_delay_ms: u32,
    inner_paths: Vec<String>,
    inner_delays_ms: Vec<u32>,
    loop_plays: u32,
    compression: u8,
    grayscale: bool,
    max_edge: u32,
) -> Result<crate::apng::ApngPreview, String> {
    let surface = PathBuf::from(&surface_path);
    if !surface.is_file() {
        return Err(format!("表图不存在: {surface_path}"));
    }
    let inner_paths_buf: Vec<PathBuf> = inner_paths.iter().map(PathBuf::from).collect();
    for p in &inner_paths_buf {
        if !p.is_file() {
            return Err(format!("里图不存在: {}", p.display()));
        }
    }

    let params = validate_and_params(
        &surface_path,
        surface_delay_ms,
        &inner_paths,
        &inner_delays_ms,
        loop_plays,
        compression,
        grayscale,
    )?;

    let res = tauri::async_runtime::spawn_blocking(move || {
        crate::apng::preview_apng(&surface, &inner_paths_buf, &params, max_edge)
    })
    .await
    .map_err(|e| e.to_string())??;

    Ok(res)
}
