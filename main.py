"""
PhantomTank - 幻影坦克图片合成工具
入口模块

原理：利用图片缩略图与原图使用不同亮度合成算法的特性，
     制作出"缩略图看到一张图、点开看到另一张图"的幻影坦克效果。

使用方式：
    python main.py              # 启动图形界面
    python main.py --debug      # 启动图形界面（调试模式）
"""

from __future__ import annotations

import sys

from gui import PhantomTankGUI


def main():
    debug_mode = "--debug" in sys.argv

    try:
        app = PhantomTankGUI(debug_mode=debug_mode)
        app.run()
    except KeyboardInterrupt:
        print("\n用户终止程序")
        sys.exit(0)
    except Exception as e:
        print(f"程序启动失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
