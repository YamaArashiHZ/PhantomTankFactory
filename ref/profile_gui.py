"""
最小化测试：排除图片处理，仅测试 sv_ttk + LabelFrame + Configure 绑定的窗口缩放性能
用法：python profile_gui.py --minimal
"""
import sys
from tkinter import Tk, ttk

def test_minimal(use_svttk=True):
    root = Tk()
    root.geometry("800x600")
    root.minsize(640, 500)

    if use_svttk:
        try:
            import sv_ttk
            sv_ttk.set_theme("light")
            print("[ON]  sv_ttk 已加载")
        except ImportError:
            print("[SKIP] sv_ttk 未安装")
    else:
        print("[OFF] sv_ttk 未加载（使用默认 ttk 主题）")

    # 构建与 gui.py 相同的结构
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    main = ttk.Frame(root, padding=12)
    main.grid(row=0, column=0, columnspan=2, sticky="nsew")
    main.columnconfigure(0, weight=1)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(0, weight=1)
    main.rowconfigure(1, weight=0)
    main.rowconfigure(2, weight=0)

    # 左预览区
    left = ttk.LabelFrame(main, text="表图 (缩略图 / 封面)", padding=5)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 8))
    left.columnconfigure(0, weight=1)
    left.rowconfigure(0, weight=1)
    left.rowconfigure(1, weight=0)

    label_a = ttk.Label(left, text="未选择\n\n\n\n\n\n\n\n\n\n", anchor="center")
    label_a.grid(row=0, column=0, sticky="nsew")
    btn_a = ttk.Button(left, text="选择表图")
    btn_a.grid(row=1, column=0, pady=(0, 4))

    # 右预览区
    right = ttk.LabelFrame(main, text="里图 (原图 / 点开后可见)", padding=5)
    right.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 8))
    right.columnconfigure(0, weight=1)
    right.rowconfigure(0, weight=1)
    right.rowconfigure(1, weight=0)

    label_b = ttk.Label(right, text="未选择\n\n\n\n\n\n\n\n\n\n", anchor="center")
    label_b.grid(row=0, column=0, sticky="nsew")
    btn_b = ttk.Button(right, text="选择里图")
    btn_b.grid(row=1, column=0, pady=(0, 4))

    # 参数区
    settings = ttk.LabelFrame(main, text="处理参数", padding=10)
    settings.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    settings.columnconfigure(1, weight=1)
    ttk.Label(settings, text="亮度增强").grid(row=0, column=0, sticky="w")
    ttk.Scale(settings, from_=0, to=100).grid(row=0, column=1, sticky="ew", padx=5)
    ttk.Label(settings, text="亮度削减").grid(row=1, column=0, sticky="w")
    ttk.Scale(settings, from_=-100, to=0).grid(row=1, column=1, sticky="ew", padx=5)

    # 按钮区
    btn_frame = ttk.Frame(main)
    btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    ttk.Button(btn_frame, text="开始合成").pack(side="left", padx=(0, 10))
    ttk.Button(btn_frame, text="打开保存目录").pack(side="left")

    # 进度条
    progress = ttk.Progressbar(main, mode="determinate")
    progress.grid(row=3, column=0, columnspan=2, sticky="ew")
    ttk.Label(main, text="就绪").grid(row=4, column=0, columnspan=2, sticky="w")

    # Configure 绑定（模拟 gui.py）
    count_a = [0]
    count_b = [0]

    def on_resize_a(e, cnt=count_a):
        cnt[0] += 1

    def on_resize_b(e, cnt=count_b):
        cnt[0] += 1

    label_a.bind("<Configure>", on_resize_a)
    label_b.bind("<Configure>", on_resize_b)

    print("\n请拖拽缩放窗口 5 秒...")
    def report():
        print(f"  Configure 事件数: 左={count_a[0]}  右={count_b[0]}")
        root.destroy()

    root.after(5000, report)
    root.mainloop()


if __name__ == "__main__":
    use_svttk = "--no-svttk" not in sys.argv
    test_minimal(use_svttk=use_svttk)
