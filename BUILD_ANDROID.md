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

### 屏幕自适应（为什么手机上画面能铺满）

游戏按 **720×820 的逻辑分辨率**渲染，再由 `pygame.SCALED` 等比铺到真实屏幕上。

这里有个坑：设计稿 720×820 的宽高比是 **0.88**（比较方），而手机竖屏普遍在
**0.43~0.56** 之间（如 1080×2400）。如果直接拿设计稿去等比缩放，画面只会占
屏幕中间一条，**上下留出大片黑边**——看起来就是"界面太小"。

解决办法是**启动时按屏幕比例动态加高逻辑画布**：

```
逻辑画布高度 = 720 × 屏幕高 / 屏幕宽      （限制在 820~2000 之间）
```

比如在 1080×2400 的机器上，逻辑画布变成 **720×1600**，宽高比与屏幕完全一致，
缩放后严丝合缝铺满，**黑边为 0**。

画布变高意味着"看得更远"，如果不做补偿，障碍从顶部落到判定线的时间会成倍变长、
游戏变得又慢又无聊。所以同时做了两件事：

- **玩家判定线**始终固定在画布底部上方 180px（角色不会飘到屏幕中间）
- **障碍速度与跳跃高度**按画布高度同比放大，保证反应时间维持在 3.2 秒左右

各机型实测（跑 `tools\test_screen_fit.py` 可复现）：

| 机型 | 逻辑画布 | 缩放 | 黑边 | 预警时间 |
| --- | --- | --- | --- | --- |
| 1080×2400 | 720×1600 | 1.50 | 0px | 3.31s |
| 1170×2532 | 720×1558 | 1.62 | 0px | 3.31s |
| 1080×2520 (21:9) | 720×1680 | 1.50 | 0px | 3.31s |
| 720×1280 | 720×1280 | 1.00 | 0px | 3.28s |
| 1440×3200 | 720×1600 | 2.00 | 0px | 3.31s |
| 2048×2732 (平板) | 720×960 | 2.84 | 1px | 3.24s |

自适应**只在真机上启用**（检测 Android 环境），电脑端保持 720×820 不变，
免得窗口被拉高后在低分辨率桌面上溢出。想在电脑上预览手机效果：

```powershell
$env:KK_FORCE_FIT = "1"
python tools\smoke_test.py
```

---

## 本地自检（不用等构建）

在电脑上先确认游戏代码本身没问题，可以跑无头冒烟测试：

```powershell
python tools\smoke_test.py
```

它会加载全部资源、跑 300 帧游戏逻辑、渲染开始/游玩/结束三个界面，
最后输出 `SMOKE OK`。改了游戏代码后建议先跑一遍再推。

重新生成应用图标：

```powershell
python tools\gen_icon.py     # 输出 icon.png（512x512）
```
