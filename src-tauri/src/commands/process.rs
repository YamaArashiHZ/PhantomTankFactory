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

#[tauri::command]
pub async fn process_phantom_tank<R: Runtime>(
    app: AppHandle<R>,
    surface_path: String,
    inner_path: String,
    brightness_enhancement: f64,
    brightness_reduction: f64,
    export_directory: String,
) -> Result<ProcessResult, String> {
    if !(0.0..=100.0).contains(&brightness_enhancement) {
        return Err("表图亮度增强须在 0~100".into());
    }
    if !(-100.0..=0.0).contains(&brightness_reduction) {
        return Err("里图亮度削减须在 -100~0".into());
    }

    let surface = PathBuf::from(&surface_path);
    let inner = PathBuf::from(&inner_path);
    if !surface.is_file() {
        return Err(format!("表图不存在: {surface_path}"));
    }
    if !inner.is_file() {
        return Err(format!("里图不存在: {inner_path}"));
    }

    let output_dir = if export_directory.trim().is_empty() {
        resolve_temp_dir(&app).map_err(|e| e)?
    } else {
        PathBuf::from(export_directory.trim())
    };

    let enhancement = brightness_enhancement;
    let reduction = brightness_reduction;

    let path = tauri::async_runtime::spawn_blocking(move || {
        phantom::process_phantom_tank(
            &surface,
            &inner,
            enhancement,
            reduction,
            &output_dir,
        )
        .map_err(|e| e.to_string())
    })
    .await
    .map_err(|e| e.to_string())??;

    Ok(ProcessResult {
        output_path: path.to_string_lossy().into_owned(),
    })
}
