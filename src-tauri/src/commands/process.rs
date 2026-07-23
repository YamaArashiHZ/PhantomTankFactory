use std::path::PathBuf;

use serde::Serialize;
use tauri::{AppHandle, Runtime};

use crate::commands::paths::resolve_temp_dir;
use crate::phantom;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProcessResult {
    pub output_path: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PreviewResult {
    /// 白底合成：缩略图/表图效果
    pub surface_preview: String,
    /// 黑底合成：点开/里图效果
    pub inner_preview: String,
}

fn validate_params(enhancement: f64, reduction: f64) -> Result<(), String> {
    if !(0.0..=100.0).contains(&enhancement) {
        return Err("表图亮度增强须在 0~100".into());
    }
    if !(-100.0..=0.0).contains(&reduction) {
        return Err("里图亮度削减须在 -100~0".into());
    }
    Ok(())
}

#[tauri::command]
pub async fn process_phantom_tank<R: Runtime>(
    app: AppHandle<R>,
    surface_path: String,
    inner_path: String,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    export_directory: String,
) -> Result<ProcessResult, String> {
    validate_params(brightness_enhancement, brightness_reduction)?;

    let surface = PathBuf::from(&surface_path);
    let inner = PathBuf::from(&inner_path);
    if !surface.is_file() {
        return Err(format!("表图不存在: {surface_path}"));
    }
    if !inner.is_file() {
        return Err(format!("里图不存在: {inner_path}"));
    }

    let output_dir = if export_directory.trim().is_empty() {
        resolve_temp_dir(&app)?
    } else {
        PathBuf::from(export_directory.trim())
    };

    let enhancement = brightness_enhancement;
    let reduction = brightness_reduction;

    let path = tauri::async_runtime::spawn_blocking(move || {
        phantom::process_phantom_tank(&surface, &inner, enhancement, reduction, &output_dir)
            .map_err(|e| e.to_string())
    })
    .await
    .map_err(|e| e.to_string())??;

    Ok(ProcessResult {
        output_path: path.to_string_lossy().into_owned(),
    })
}

#[tauri::command]
pub async fn preview_phantom_tank(
    surface_path: String,
    inner_path: String,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    max_edge: u32,
) -> Result<PreviewResult, String> {
    validate_params(brightness_enhancement, brightness_reduction)?;

    let surface = PathBuf::from(&surface_path);
    let inner = PathBuf::from(&inner_path);
    if !surface.is_file() {
        return Err(format!("表图不存在: {surface_path}"));
    }
    if !inner.is_file() {
        return Err(format!("里图不存在: {inner_path}"));
    }

    let enhancement = brightness_enhancement;
    let reduction = brightness_reduction;

    let (surface_preview, inner_preview) = tauri::async_runtime::spawn_blocking(move || {
        phantom::preview_phantom_tank(&surface, &inner, enhancement, reduction, max_edge)
            .map_err(|e| e.to_string())
    })
    .await
    .map_err(|e| e.to_string())??;

    Ok(PreviewResult {
        surface_preview,
        inner_preview,
    })
}
