# 将《坤坤大逃亡》打包为 Android APK

pygame 游戏转 APK 需要 **Buildozer / python-for-android**，它们**只能在 Linux 上运行**。
本项目已准备好全部文件，你任选下面一种方式即可得到 APK。

## 项目文件结构（须保持在同一目录）

```
├── main.py                # Android 入口（buildozer 强制要求此文件名）
├── kunkun_da_tao_wang.py  # 游戏主程序
├── buildozer.spec         # 打包配置
├── kk.jpg / shallwe.jpg / huazhao.jpg   # 人物头像
├── bgm.mp3 / get.mp3 / music.mp3        # 音效（建议另备 ogg 版本，见下）
└── font.otf / font.ttf    # 中文字体（强烈建议添加，见下）
```

## 方式 A：本机 Linux + Buildozer（推荐在 WSL2/Ubuntu 虚拟机里做）

```bash
# 1) 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git zip unzip openjdk-17-jdk     build-essential autoconf libtool pkg-config zlib1g-dev libncurses5-dev     libncursesw5-dev cmake libffi-dev libssl-dev

# 2) 安装 buildozer
python3 -m pip install --upgrade buildozer cython

# 3) 打包（首次会自动下载 Android SDK/NDK，耗时约 20~40 分钟）
buildozer android debug
```

打包完成后 APK 在 `bin/kunkundaotao-0.1-arm64-v8a_armeabi-v7a-debug.apk`。

## 方式 B：GitHub Actions 自动打包（无需 Linux 电脑）

1. 把整个目录推送到一个 GitHub 仓库（仓库根目录就是这些文件）。
2. 仓库已含 `.github/workflows/build-apk.yml`，每次 push 会自动在 Linux 上构建。
3. 打开仓库 **Actions** → 该次运行的 **Artifacts** 即可下载 APK。

## 两个重要注意点

### 1) 中文字体（否则手机上中文会显示成方块 □）
Android 系统没有游戏用的中文字体，必须自带一个。请下载任意中文字体（例如
**Noto Sans SC**：https://github.com/googlefonts/noto-cjk 的
`Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf`），
放到项目根目录并重命名为 `font.otf`（或 `font.ttf`）。游戏会自动加载它。

### 2) 音效格式（mp3 在 Android 上可能无声）
Buildozer 的 pygame 依赖 SDL_mixer，默认常不带 mp3 解码器。建议把
`bgm.mp3 / get.mp3 / music.mp3` 额外转成 `.ogg` 或 `.wav` 一起放进目录，
游戏会按 `ogg → wav → mp3` 顺序自动选择。若没有，游戏仍可正常运行，只是静音。

## 手机操作方式

- 左滑 / 右滑（或点屏幕左 1/3 / 右 1/3）：切换跑道
- 上滑（或点屏幕中间）：跳跃
- 点屏幕：开始 / 重新开始

（电脑上仍可用 ←→/A/D 换道、↑/W/空格 跳跃。）

## 安装到手机

```bash
adb install bin/*.apk        # 需要开启 USB 调试
```
或把 APK 文件发到手机上，允许「安装未知来源应用」后点击安装。
