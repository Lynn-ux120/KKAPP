# 把《坤坤大逃亡》打包成 Android APK

## 现状说明（重要）

pygame 转 APK 依赖 **Buildozer / python-for-android**，它们**只能在 Linux 上运行**。

本机（Windows）目前的状况：

| 方案 | 是否可用 | 原因 |
| --- | --- | --- |
| WSL2 + Buildozer | ❌ | `wsl.exe` 被本机安全策略（程序黑名单）拦截 |
| Docker + Buildozer 镜像 | ❌ | 未安装 Docker |
| 本机直装 JDK/SDK/NDK | ❌ | Buildozer 本身不支持 Windows |
| **GitHub Actions 云构建** | ✅ | 无需本机 Linux，已配置好 |

所以本项目采用**方式 B：GitHub Actions 自动构建**。推送代码后，云端 Linux
会自动编译出 APK。

---

## 方式 B：GitHub Actions 自动打包（当前采用）

仓库：<https://github.com/Lynn-ux120/KKAPP>

1. 把改动推上去（见下方「如何触发构建」）。
2. 打开仓库的 **Actions** 页签，会看到名为 **Build Android APK** 的工作流在跑。
3. 首次构建约 **30~60 分钟**（要下载 Android SDK/NDK 并编译 Python 与 pygame）；
   之后有缓存，会快不少。
4. 构建成功后，点进那次运行，在页面底部 **Artifacts** 区下载
   `kunkundaotao-apk`，解压得到 `.apk` 文件。

### 如何触发构建

- **自动**：向 `main` 分支 push 且改动了 `.py` / `buildozer.spec` / 图片 / 音频 / 字体时自动触发。
- **手动**：仓库 → Actions → 左侧选 `Build Android APK` → 右侧 `Run workflow`。

命令行推送（本机已配好 remote）：

```powershell
cd "D:\KK大逃亡"
git add -A
git commit -m "更新游戏"
git push
```

> 推送时会要求输入 GitHub 用户名和 **Personal Access Token**（不是登录密码）。
> Token 需要勾选 `repo`（私有库）或 `public_repo`（公开库）权限。

---

## 安装到手机

下载到 APK 后，两种装法：

**A. 数据线（推荐，可看日志）**

```bash
adb install -r kunkundaotao-1.0-arm64-v8a_armeabi-v7a-debug.apk
```

**B. 直接把 APK 发到手机上**
用微信/QQ/网盘传到手机 → 点击安装 → 允许「安装未知来源应用」。

> 这是 **debug 签名**的 APK，只能侧载安装，不能上架应用商店。
> 若要上架，需要改成 `buildozer android release` 并配置正式签名密钥。

---

## 打包配置里的关键点（改坏了会构建失败）

都写在 `buildozer.spec` 里，几个容易踩的坑：

1. **`python3` 和 `hostpython3` 必须锁成同一个版本 `3.10.13`**
   p4a 自带的 pygame 配方版本是 **2.1.0**，只支持到 Python 3.10；
   而 p4a 现在的默认 Python 已经是 **3.14.2**。不锁版本必挂。

   而且两个都要锁——`hostpython3` 是构建期用的 Python，只锁 `python3` 会报：
   ```
   Build failed: python3 should have same version as hostpython3, 3.10.13 != 3.14.2
   ```

2. **Cython 必须锁在 3.0 以下**
   `Cython 3.x` 移除了 `longintrepr.h`，会直接把 pygame/kivy 配方编崩。
   工作流里已固定 `Cython<3.0`。

3. **`android.api = 33` 配合 `android.ndk = 25b`**
   NDK r25b 最高只支持 API 33；写更高的 API 会找不到平台库。

4. **`android.accept_sdk_license = True`**
   没有这行，CI 会在「接受 SDK 许可证」那一步卡住直到超时。

5. **源码文件名必须是纯 ASCII**
   所以真正的游戏代码叫 `kunkun_da_tao_wang.py`；
   根目录那个 `KK大逃亡（点我运行）.py` 只是给电脑上双击用的启动器。

6. **中文字体已内置**
   `font.otf`（约 16 MB）会打进 APK，否则手机上中文全是方块 □。

---

## 方式 A：本机 Linux + Buildozer（备选）

如果你以后装了 WSL2 或换了 Linux 机器，按下面做会更快（不用等 CI）：

```bash
# 1) 系统依赖
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git zip unzip \
  openjdk-17-jdk build-essential autoconf automake libtool pkg-config \
  zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev liblzma-dev

# 2) 安装 buildozer（注意 Cython 版本）
python3 -m pip install --upgrade pip
python3 -m pip install "Cython<3.0" "setuptools<71" buildozer

# 3) 打包（首次会下载 Android SDK/NDK，约 20~40 分钟）
cd "/mnt/d/KK大逃亡"     # WSL 里的路径
yes | buildozer -v android debug
```

产物：`bin/kunkundaotao-1.0-arm64-v8a_armeabi-v7a-debug.apk`

---

## 手机操作方式

- **左滑 / 右滑**（或点屏幕左 1/3 / 右 1/3）：切换跑道
- **上滑**（或点屏幕中间）：跳跃
- **点屏幕**：开始 / 重新开始

电脑上仍可用 ←→/A/D 换道、↑/W/空格 跳跃。

### 屏幕自适应（为什么手机上画面既铺满又清晰）

游戏逻辑画布**不再固定 720×820**，而是启动时按屏幕真实分辨率决定：

```
缩放系数  = 屏幕宽 / 720
逻辑画布  = (720 × 缩放系数, 屏幕高 × 缩放系数)
```

配合 `pygame.SCALED`，画布与屏幕就是 **1:1 原生渲染**，画面不存在"小画布放大"
带来的模糊——这就是**清晰度提升**的来源。

设计稿 720×820 的宽高比是 **0.88**（比较方），而手机竖屏普遍在 **0.43~0.56**
之间（如 1080×2400）。若直接拿设计稿等比缩放，画面只会占屏幕中间一条，
上下留大片黑边（就是之前"界面太小"的原因）。按上面的公式动态定画布，
宽高比与屏幕完全一致，**黑边为 0**。

画布变高意味着"看得更远"，不做补偿的话障碍落到判定线的时间会成倍变长、
游戏变得又慢又无聊。所以同时做了两件事：

- **玩家判定线**始终固定在画布底部上方，角色不会飘到屏幕中间
- **障碍速度与跳跃高度**按画布高度同比放大，保证反应时间稳定在 3.2 秒左右

各机型实测（跑 `tools\test_screen_fit.py` 可复现）：

| 机型 | 逻辑画布 | 放大 | 黑边 | 预警时间 |
| --- | --- | --- | --- | --- |
| 1080×2400 | 1080×2400 | 1.00 | 0px | 3.31s |
| 1170×2532 (iPhone) | 1170×2532 | 1.00 | 0px | 3.31s |
| 1080×2520 (21:9) | 1080×2520 | 1.00 | 0px | 3.31s |
| 720×1280 (老机型) | 720×1280 | 1.00 | 0px | 3.28s |
| 1440×3200 (2K) | 1200×2666 | 1.20 | 0px | 3.31s |
| 2048×2732 (平板) | 1549×2066 | 1.32 | 0px | 3.24s |

主流机型都是 **1.00 倍原生渲染**；2K/平板因为软件渲染性能上限会轻微降采样，
避免帧率掉下去。难度漂移 3.3%，各机型手感一致。

自适应**只在真机上启用**（检测 Android 环境），电脑端保持设计稿尺寸不变，
免得窗口被拉高后在低分辨率桌面上溢出。想在电脑上预览手机效果：

```powershell
$env:KK_FORCE_FIT = "1"
python tools\smoke_test.py
```

### 流畅度优化（为什么帧率稳）

在软件渲染（Android 端没有 GPU 加速的 `SDL_Renderer`）下，**每帧新建 Surface
是最贵的开销**。游戏里所有"每帧都长一样"的东西都改成预渲染 + 缓存：

| 优化项 | 做法 |
| --- | --- |
| 静态背景、跑道分隔线 | 预渲染整张 Surface，每帧只 1 次 blit |
| 路面标线 | 预渲染一格后垂直平铺，省掉每帧几十次 `draw.rect` |
| 侧边栏静态部分 | 预渲染整张，只有数值部分动态画 |
| 半透明遮罩（开始/结束/凝视） | 预渲染复用，不再每帧全屏建 Surface |
| 文字 | 按 (文本, 字号, 颜色) 缓存渲染结果 |
| 椭圆阴影、道具光晕、按钮面板/光晕/按下态 | 全部预渲染并缓存 |

实测（`tools\test_perf.py`，无头软件渲染，最坏情况）：

```
主流 1080x2400    平均 5.08 ms/帧  ≈ 197 FPS
2K 1440x3200      平均 6.09 ms/帧  ≈ 164 FPS
```

60 FPS 的预算是 16.7 ms/帧，还有 3 倍余量。

### 加载动画

启动时不再直接黑屏等资源加载，而是**分批加载 + 进度条动画**：

```
初始化音频 → 加载角色 → 加载班主任与校长 → 生成跑道
```

每一步之间有平滑推进的进度条、当前步骤文字、百分比和一个跑动的小人，
既遮住了加载耗时，也让玩家知道没卡死。加载耗时约 0.5~1.1 秒。

### 菜单按钮

`开始游戏` / `再玩一次` / `退出游戏` 都做成了**可点击按钮**（`Button` 类）：

- 金色主按钮 + 暗色次按钮，带呼吸光晕
- 鼠标悬停高亮（电脑端）、按下压暗反馈
- 触摸与鼠标事件统一走 `Button.hit()` 命中检测，手机上点按即可
- 键盘快捷键仍然保留（空格开始、R 重开、ESC 退出）

---

## 本地自检（不用等构建）

在电脑上先确认游戏代码本身没问题，可以跑无头冒烟测试：

```powershell
python tools\smoke_test.py        # 加载资源 + 跑逻辑 + 渲染三界面，输出 SMOKE OK
python tools\test_screen_fit.py   # 各机型铺满/清晰度/难度一致性
python tools\test_perf.py         # 渲染性能基准
python tools\preview_ui.py        # 生成各界面截图到 tools\preview\
```

改了游戏代码后建议先跑前三个再推。

重新生成应用图标：

```powershell
python tools\gen_icon.py     # 输出 icon.png（512x512）
```
