"""
PhantomTank 日志模块
提供带色彩的控制台日志输出，以及调试模式下的文件日志
日志文件保存在 logs/ 目录下
"""

import os
import time
import logging
from pathlib import Path

import colorama
from colorama import Fore, Style


def init_logger(debug_mode: bool = False) -> logging.Logger:
    """
    初始化并返回全局 logger 实例

    控制台输出：
      - debug_mode=True 时显示所有级别日志（含 DEBUG）
      - debug_mode=False 时仅显示 INFO 及以上

    文件输出：
      - 仅在 debug_mode=True 时启用，保存至 logs/ 目录
    """
    colorama.init()

    logger = logging.getLogger("PhantomTank")
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if logger.handlers:
        logger.handlers.clear()

    # ---- 控制台 handler (带颜色) ----
    console_level = logging.DEBUG if debug_mode else logging.INFO

    console_formatter = logging.Formatter(
        Fore.LIGHTBLUE_EX + "[%(asctime)s] [%(levelname)s] %(message)s" + Style.RESET_ALL,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)

    # ---- 文件 handler (仅调试模式) ----
    if debug_mode:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%y-%m-%d_%H%M%S", time.localtime())
        log_path = log_dir / f"log_{timestamp}.log"

        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    return logger
