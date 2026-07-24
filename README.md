# PhantomTank Factory

[![CI](https://github.com/YamaArashiHZ/PhantomTankFactory/actions/workflows/ci.yml/badge.svg)](https://github.com/YamaArashiHZ/PhantomTankFactory/actions/workflows/ci.yml)

幻影坦克合成工具 —— 选择表图与里图，生成「缩略图看一张、点开看另一张」的 PNG。

> 本仓库当前主开发线为 **Tauri 2 + Vue 3 + Rust** 重写版。

## 下载安装（Windows）

普通用户请直接从 **Latest Release** 下载安装包，无需自行编译：

**→ [Latest Release](https://github.com/YamaArashiHZ/PhantomTankFactory/releases/latest)**

1. 打开上方链接（或仓库页右侧 **Releases** → **Latest**）
2. 下载 `PhantomTank Factory_x.x.x_x64-setup.exe`（安装程序）
3. 运行安装程序，按提示完成安装

系统要求：Windows 10/11 x64，已安装 [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/)（多数系统已自带）。

## 功能

- 表图 / 里图选择与预览
- 亮度参数调节
- 实时效果预览（白底表图 / 黑底里图，可开关与清晰度档位）

## 技术栈

- **桌面壳**：Tauri 2
- **前端**：Vue 3、TypeScript、Naive UI、Vite
- **图像处理**：Rust（`image` crate）
- **包管理**：pnpm

## 环境要求（开发）

- Node.js（LTS）+ pnpm
- Rust（stable）
- Windows：Visual Studio Build Tools（C++ 桌面开发）
- WebView2（Win10/11 通常已自带）

## 开发

```bash
pnpm install
pnpm tauri dev
```

### Pre-commit Hooks

安装 [lefthook](https://github.com/evilmartians/lefthook) 后执行：

```bash
lefthook install
```

之后每次 `git commit` 自动运行 `cargo fmt --check` + `vue-tsc --noEmit`。

## 打包

```bash
pnpm tauri build
# 或仅 NSIS 安装包：
pnpm tauri build --bundles nsis
```

Windows 安装包一般在：

```text
src-tauri/target/release/bundle/nsis/
```

示例文件名：`PhantomTank Factory_0.1.0_x64-setup.exe`

## 配置文件位置

用户配置由 Tauri Store 保存，Windows 大致路径：

```text
%APPDATA%\com.phantomtank.factory\settings.json
```

## 作者

- YamaArashi
- GitHub：https://github.com/YamaArashiHZ/PhantomTankFactory

## 许可证

[MIT](./LICENSE)
