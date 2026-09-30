# 《坤坤大逃亡》—— 校园大逃亡 · 无尽竖版跑酷

基于 Python + pygame 编写的无尽竖版跑酷小游戏。

## 运行前准备

1. 安装 Python（3.8 及以上版本均可）。
2. 安装 pygame：

   ```
   pip install pygame
   ```

   如果 Python 版本较新（如 3.13 / 3.14）官方 pygame 没有对应安装包，
   可改用社区维护版 pygame-ce：

   ```
   pip install pygame-ce
   ```

   （代码里 `import pygame` 对两者都通用。）

3. 确保以下图片与脚本放在同一目录：

   - `kk.jpg`         —— 玩家“坤坤”
   - `shallwe.jpg`    —— 追逐者“班主任 shall we”
   - `huazhao.jpg`    —— 追逐者“校长花招”

   图片缺失时程序会自动用纯色矩形兜底，不会崩溃。

## 运行

```
python kunkun_da_tao_wang.py
```

也可以直接双击根目录的 `KK大逃亡（点我运行）.py`——它只是个启动器，
真正的游戏代码在 `kunkun_da_tao_wang.py`（打包 APK 要求源码文件名是纯 ASCII）。

```text
kunkun_da_tao_wang.py            ← 游戏主程序（改代码改这里）
KK大逃亡（点我运行）.py            ← 电脑端双击启动器
main.py                          ← Android 打包入口
buildozer.spec                   ← APK 打包配置
icon.png                         ← 应用图标（用 tools/gen_icon.py 生成）
tools/smoke_test.py              ← 无头冒烟测试
tools/test_screen_fit.py         ← 各机型铺满 / 清晰度 / 难度一致性
tools/test_perf.py               ← 渲染性能基准
tools/preview_ui.py              ← 生成各界面截图（输出到 tools/preview/）
tools/gen_icon.py                ← 重新生成图标
```

## 界面与手感

- **清晰**：逻辑画布按屏幕真实分辨率设定，配合 `pygame.SCALED` 是 1:1 原生渲染，
  主流机型（1080×2400 等）不做任何放大，也不留黑边。
- **流畅**：背景、路面、侧边栏、遮罩、文字、阴影、光晕全部预渲染缓存，
  每帧只做 blit。实测 ≈200 FPS（60 FPS 的预算是 16.7 ms/帧）。
- **加载动画**：启动时分批加载资源，带进度条、当前步骤和跑动小人。
- **按钮化菜单**：开始 / 重开 / 退出都是可点击按钮，带呼吸光晕、
  悬停高亮和按下反馈，触摸与鼠标通用。

## 操作方式

| 操作 | 作用 |
| --- | --- |
| 左 / 右方向键 或 A / D | 在 3 条跑道间切换（切换会重置凝视倒计时） |
| 上方向键 / W / 空格 | 跳跃（可跳过矮障碍：黑板擦、试卷） |
| ESC | 退出游戏 |
| R（游戏结束后） | 重新开始 |
| 点「开始游戏」/「再玩一次」按钮 | 开始 / 重新开始 |

手机上：**左右滑**换道，**上滑或点中间**跳跃，**点按钮**开始 / 重开 / 退出。

## 玩法要点

- 障碍物：课桌（高，必须换道）、黑板擦与试卷（矮，可跳过）。
- 道具：咖啡（短暂双倍得分加速）、辣条（短暂无敌）。
- 班主任的凝视：连续 5 秒不切换跑道，班主任与校长会加速逼近。
- 难度随时间递增，速度越来越快。

## 打包成安卓 APK

见 [BUILD_ANDROID.md](BUILD_ANDROID.md)。

简单说：Buildozer 只能在 Linux 上跑，本机 Windows 走不通，所以用
**GitHub Actions 云构建** —— push 到 `main` 分支后，去仓库的 Actions 页
下载编译好的 APK 即可。

手机上：左右滑换道、上滑或点中间跳跃、点屏幕开始。

## 本地自检

改完代码先跑一遍，能提前发现资源缺失或渲染错误：

```
python tools/smoke_test.py        # 资源 + 逻辑 + 三界面渲染
python tools/test_screen_fit.py   # 屏幕适配与清晰度
python tools/test_perf.py         # 帧率基准
python tools/preview_ui.py        # 出界面截图，肉眼验收布局
```

前三个输出 `SMOKE OK` / `SCREEN FIT OK` / `PERF OK` 即正常。
