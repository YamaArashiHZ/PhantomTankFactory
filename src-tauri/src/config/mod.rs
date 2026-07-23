use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppConfig {
    pub brightness_enhancement: f64,
    pub brightness_reduction: f64,
    pub export_directory: String,
    pub theme: String,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            brightness_enhancement: 50.0,
            brightness_reduction: -50.0,
            export_directory: String::new(),
            theme: "light".to_string(),
        }
    }
}
