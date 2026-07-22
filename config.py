"""
PhantomTank 配置管理模块
负责读取、写入、校验 YAML 配置文件
"""

import os
import yaml
from pathlib import Path


# 默认配置内容（用于首次生成配置文件）
DEFAULT_CONFIG_YAML = """\
# PhantomTank 配置文件
# 亮度增强 (表面图) 范围: 0 ~ 100
brightness_enhancement: 50

# 亮度削减 (里图) 范围: -100 ~ 0
brightness_reduction: -50

# 导出目录 (留空则保存至程序所在目录)
export_directory: ""

# 调试模式
debug_mode: false
"""


class Config:
    """配置管理类，封装 YAML 配置的读取、写入与校验"""

    CONFIG_FILE = "PTM_config.yml"

    def __init__(self):
        self.data = {}
        self._ensure_config_exists()
        self.load()

    def _ensure_config_exists(self):
        """若配置文件不存在，则使用默认内容创建"""
        config_path = Path(self.CONFIG_FILE)
        if not config_path.exists():
            config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")

    def load(self):
        """从 YAML 文件加载配置"""
        with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}

        # 校验并补全缺失项
        self._validate_and_fill()

    def save(self):
        """将当前配置写入 YAML 文件"""
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(self.data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _validate_and_fill(self):
        """校验配置项合法性，不合法则重置为默认值"""
        defaults = {
            "brightness_enhancement": 50,
            "brightness_reduction": -50,
            "export_directory": "",
            "debug_mode": False,
        }
        for key, default in defaults.items():
            if key not in self.data:
                self.data[key] = default
                continue
            # 校验亮度参数范围
            if key == "brightness_enhancement":
                if not isinstance(self.data[key], (int, float)) or not (0 <= self.data[key] <= 100):
                    self.data[key] = default
            if key == "brightness_reduction":
                if not isinstance(self.data[key], (int, float)) or not (-100 <= self.data[key] <= 0):
                    self.data[key] = default

    # ---- 便捷属性 ----

    @property
    def brightness_enhancement(self) -> float:
        """亮度增强值 (0~100)"""
        return float(self.data.get("brightness_enhancement", 50))

    @brightness_enhancement.setter
    def brightness_enhancement(self, value: float):
        if 0 <= value <= 100:
            self.data["brightness_enhancement"] = float(value)
        else:
            raise ValueError(f"brightness_enhancement 超出范围 0~100: {value}")

    @property
    def brightness_reduction(self) -> float:
        """亮度削减值 (-100~0)"""
        return float(self.data.get("brightness_reduction", -50))

    @brightness_reduction.setter
    def brightness_reduction(self, value: float):
        if -100 <= value <= 0:
            self.data["brightness_reduction"] = float(value)
        else:
            raise ValueError(f"brightness_reduction 超出范围 -100~0: {value}")

    @property
    def export_directory(self) -> str:
        """导出目录路径"""
        return str(self.data.get("export_directory", ""))

    @export_directory.setter
    def export_directory(self, value: str):
        self.data["export_directory"] = str(value)

    @property
    def debug_mode(self) -> bool:
        """是否开启调试模式"""
        return bool(self.data.get("debug_mode", False))

    @debug_mode.setter
    def debug_mode(self, value: bool):
        self.data["debug_mode"] = bool(value)
