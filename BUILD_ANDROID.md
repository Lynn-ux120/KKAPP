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
- **点「开始游戏」/「再玩一次」/「退出游戏」按钮**：菜单操作
  （点按钮以外的空白处也同样开始 / 重开，避免手指没点准就没反应）

键盘快捷键仍然保留：←→/A/D 换道、↑/W/空格 跳跃、空格开始、R 重开、ESC 退出。

### 掉帧是怎么解决的（重要，别改回去）

**根因**：上一版为了追求"原生清晰度"，把逻辑画布放大到屏幕物理分辨率
（1080×2400 ≈ **260 万像素**）。但 **pygame 是 CPU 软件渲染**，画布越大，
每帧要写入的像素越多——背景 1 次全屏 blit、路面标线二十来次平铺、侧边栏、
遮罩……加起来每帧近千万像素，手机上必然掉帧。

**改法**：画布宽度固定 **720**，高度按屏幕比例算：

```
画布宽高比 = 屏幕宽高比       →  主流机型 720×1600 ≈ 115 万像素
```

绘制量降到原来的约 **1/3**（115 万 vs 260 万），清晰度改由 `pygame.SCALED`
交给 GPU 缩放来保证。这是本次"流畅度提升"的核心。

用 `tools\profile_frame.py` 实测各环节耗时（1080×2400 机型，无头软件渲染）：

| 环节 | 耗时 | 说明 |
| --- | --- | --- |
| 背景 blit | 0.67 ms | 必需开销，1:1 无缩放拷贝 |
| 路面标线 | 0.20 ms | 只 blit 标线本体，不含空白间隔 |
| 顶部 HUD | 0.12 ms | 文字走缓存 |
| 全部角色/障碍/粒子 | 0.21 ms | |
| **SDL 缩放输出（flip）** | **4.20 ms** | 交给 GPU 后基本不占 CPU |

也就是说**绘制只占约 1.2 ms，大头是 SDL 把画面缩放到屏幕物理分辨率**。
这部分在有 OpenGL 的设备上走 GPU，是免费的；真机上若仍然掉帧，
就说明设备回退到了软件 renderer，此时唯一的办法是把画布再调小
（见 `kunkun_da_tao_wang.py` 顶部 `DESIGN_W` 的注释）。

### 画面为什么能铺满全屏（不再有黑边）

两个条件缺一不可：

1. **画布宽高比 = 屏幕宽高比**
   画布高度取 `720 × 屏幕高 / 屏幕宽`（限制在 820~1800 之间），
   比例对上了才可能严丝合缝。

2. **把 SDL 的缩放模式改成 `overscan`**
   `pygame.SCALED` 默认是 **letterbox**——保持宽高比、多余部分**填黑边**，
   这正是"画面撑不满全屏"的元凶。设成 overscan 后 SDL 会直接拉伸铺满。
   由于第 1 条已经保证比例一致，拉伸不会造成任何形变。

   代码在文件顶部：
   ```python
   os.environ.setdefault("SDL_RENDER_LOGICAL_SIZE_MODE", "overscan")
   ```
   必须在创建窗口之前设置。

   尺寸探测失败时（拿不到屏幕分辨率）会自动退回 letterbox ——
   那种情况下画布是设计稿比例、和屏幕对不上，留黑边总好过把画面拉变形。

设计稿 720×820 的宽高比是 0.88（很方），手机竖屏普遍在 0.43~0.56。
早先直接拿设计稿等比缩放，画面只占屏幕中间一条、上下大片黑边，
"界面太小"就是这么来的。

画布变高意味着"看得更远"，不做补偿的话障碍落到判定线的时间会成倍变长、
游戏变得又慢又无聊。所以同时做了两件事：

- **玩家判定线**始终固定在画布底部上方 180px，角色不会飘到屏幕中间
- **障碍速度**按画布高度同比放大，保证反应时间稳定在 3.2 秒左右

各机型实测（跑 `tools\test_screen_fit.py` 可复现）：

| 机型 | 逻辑画布 | 比例偏差 | 画布像素 | 预警时间 |
| --- | --- | --- | --- | --- |
| 1080×2400 | 720×1600 | 0.00% | 1.15M | 3.31s |
| 1170×2532 (iPhone) | 720×1558 | 0.01% | 1.12M | 3.31s |
| 1080×2520 (21:9) | 720×1680 | 0.00% | 1.21M | 3.31s |
| 720×1280 (老机型) | 720×1280 | 0.00% | 0.92M | 3.28s |
| 2048×2732 (平板) | 720×960 | 0.05% | 0.69M | 3.24s |
| 2400×1080（被报成横屏） | 720×1600 | 0.00% | 1.15M | 3.31s |

难度漂移 3.5%，各机型手感一致。

自适应**只在真机上启用**（检测 Android 环境），电脑端保持 720×820 不变，
免得窗口被拉高后在低分辨率桌面上溢出。想在电脑上预览手机效果：

```powershell
$env:KK_FORCE_FIT = "1"
python tools\smoke_test.py
```

### 其他渲染优化

在软件渲染下，**每帧新建 Surface 是最贵的开销**。所有"每帧都长一样"的东西
都改成了预渲染 + 缓存：

| 优化项 | 做法 |
| --- | --- |
| 静态背景、跑道分隔线 | 预渲染整张 Surface，每帧只 1 次 blit |
| 路面标线 | 预渲染**标线本体**后按间隔竖直平铺；只做 26px 高而非整段 78px 间隔，少处理 2/3 透明像素 |
| 顶部 HUD 压暗条 | 预渲染整张，每帧 1 次 blit |
| 半透明遮罩（开始/结束/凝视） | 预渲染复用，不再每帧全屏建 Surface |
| 文字 | 按 (文本, 字号, 颜色) 缓存，且用 **LRU 淘汰**而非"满了整体清空"——得分/时间这类每帧都在变的文本会不断产生新条目，整体清空会让所有静态文案一起重渲染，造成周期性掉帧尖峰 |
| 椭圆阴影、道具光晕、按钮面板/光晕/按下态 | 全部预渲染并缓存 |

实测（`tools\test_perf.py`）：主流 1080×2400 约 **5.0 ms/帧（≈200 FPS）**，
2K 1440×3200 约 **5.4 ms/帧**。60 FPS 的预算是 16.7 ms/帧，余量 3 倍以上。

### 界面布局的两处调整

- **右侧键位说明栏已移除**。原先它常驻屏幕右侧、挤占跑道，手机上又小得看不清。
  现在跑道铺满全宽，障碍相应加宽（150px）；状态信息全部改到顶部横条：
  得分 / 最高分 / 时间 / 凝视倒计时进度条 / 无敌与加速剩余时间。
- **操作与规则提醒前移到开始界面**。开始游戏前用一块面板集中展示键位
  （换道、跳跃、触屏手势）和玩法（障碍类型、凝视机制、道具效果），
  进入游戏后画面全部留给跑道。

### 加载动画

启动时不再黑屏干等资源加载，而是**分批加载 + 进度条动画**：

```
初始化音频 → 加载角色 → 加载班主任与校长 → 生成跑道
```

界面以 `loading_bg.png`（由 `beijing.png` 去水印后生成）为全屏背景，
下方是金色进度条、当前步骤文字、百分比和一个跑动的小人，
既遮住了加载耗时，也让玩家知道没卡死。加载耗时约 0.5~1.3 秒。

背景图是 720×1280（9:16），而画布多在 20:9 上下——比例对不上时，
底部那一截是**把图片最下缘纵向拉伸**补齐的（原图底部本来就是铁轨，
拉长后近似运动模糊，看不出接缝）。别改回"填纯色块"，
源图底部有亮色铁轨，填出来的色带会留一道明显的分界。

`buildozer.spec` 里的 `presplash` 也用的这张图——这样 Android 启动闪屏
和游戏内加载界面是同一画面，切换时没有突兀感。

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
python tools\smoke_test.py        # 加载资源 + 跑逻辑 + 渲染四界面 + 按钮，输出 SMOKE OK
python tools\test_screen_fit.py   # 各机型比例匹配 / 画布像素量 / 难度一致性
python tools\test_perf.py         # 渲染性能基准
python tools\profile_frame.py     # 逐帧耗时分解（怀疑掉帧时先跑这个）
python tools\preview_ui.py        # 生成各界面截图到 tools\preview\
```

改了游戏代码后建议先跑前面几个再推。

### 重新生成图标与加载背景

源图放在工程根目录：`kkphoto.png`（图标）、`beijing.png`（加载背景）。
脚本会先抹掉两张图右下角的「千问」水印，再输出 `icon.png`（512×512）
和 `loading_bg.png`：

```powershell
python tools\prep_assets.py
```

去水印用的是拉普拉斯平滑——以水印矩形四周像素为边界条件向内部迭代扩散。
如果换了新的源图，改一下脚本顶部的 `ICON_WM` / `BG_WM` 两个矩形坐标即可。
