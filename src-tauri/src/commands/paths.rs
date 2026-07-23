use std::path::PathBuf;

use tauri::{AppHandle, Manager, Runtime};

/// 开发模式：项目根目录下的 temp/  
/// 安装版：AppData 下的 temp/
#[tauri::command]
pub fn get_temp_dir<R: Runtime>(app: AppHandle<R>) -> Result<String, String> {
    let path = resolve_temp_dir(&app)?;
    std::fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    Ok(path.to_string_lossy().into_owned())
}

pub fn resolve_temp_dir<R: Runtime>(app: &AppHandle<R>) -> Result<PathBuf, String> {
    if cfg!(debug_assertions) {
        // src-tauri 的上一级即项目根
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .map(|p| p.to_path_buf())
            .ok_or_else(|| "无法解析项目根目录".to_string())?;
        Ok(root.join("temp"))
    } else {
        let app_data = app.path().app_data_dir().map_err(|e| e.to_string())?;
        Ok(app_data.join("temp"))
    }
}

/// 默认导出目录：用户图片目录，失败则用文档目录。
#[tauri::command]
pub fn get_default_export_dir<R: Runtime>(app: AppHandle<R>) -> Result<String, String> {
    let dir = app
        .path()
        .picture_dir()
        .or_else(|_| app.path().document_dir())
        .map_err(|e| e.to_string())?;
    Ok(dir.to_string_lossy().into_owned())
}
