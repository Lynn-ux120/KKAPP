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
icon.png                         ← 应用图标（由 kkphoto.png 生成）
loading_bg.png                   ← 启动加载界面背景（由 beijing.png 生成）
tools/smoke_test.py              ← 无头冒烟测试
tools/test_screen_fit.py         ← 各机型铺满 / 像素量 / 难度一致性
tools/test_perf.py               ← 绘制耗时基准（flip 单独参考）
tools/profile_frame.py           ← 逐帧耗时分解，定位性能瓶颈
tools/bench_render.py            ← 凝视开销分解 + RENDER_SCALE 倍率扫描
tools/bench_flip.py              ← flip 缩放成本 vs 画布尺寸 / 滤波质量
tools/preview_ui.py              ← 生成各界面截图（输出到 tools/preview/）
tools/prep_assets.py             ← 抹水印并生成图标 / 加载背景
```

## 界面与手感

- **清晰度 / 帧速率的唯一旋钮 `RENDER_SCALE`**：pygame 是 CPU 软件渲染，
  画布像素总量直接决定帧率，画布又不能太小（会被 SDL 放大后发虚）。
  所以钉死"设计稿宽 720"，再用 `RENDER_SCALE` 把整套美术、字号、间距
  一起放大到目标画布分辨率——布局比例永远不变，只是像素密度变高。

  | RENDER_SCALE | 画布宽 | 1080 屏上的放大倍数 | 像素量（20:9） | 适合 |
  | --- | --- | --- | --- | --- |
  | 1.00 | 720 | 1.50×（偏软） | 1.15M | 老旧机型 |
  | **1.25（当前）** | **900** | **1.20×** | **1.80M** | **主流机型** |
  | 1.50 | 1080 | 1.00×（最锐） | 2.59M | 旗舰机 |

  真机若仍掉帧就把这个数调小，觉得不够锐就调大；改一个常数即可，布局代码不用动。
  临时试数值也可以不改代码：`KK_RENDER_SCALE=1.0 python kunkun_da_tao_wang.py`。
- **铺满全屏**：画布宽高比刻意做得与屏幕完全一致，且把 SDL 的缩放模式设为
  overscan，缩放后严丝合缝、不留黑边。
- **凝视不掉帧**：凝视时不再在整屏叠一层半透明红罩（实测 0.65 ms/帧，是凝视态
  最贵的一步），而是预先烘出一张偏红的背景图，用时直接换图（0.16 ms）。
  凝视态的额外开销从 +1.45 ms 降到 ≈0.3 ms。
- **预渲染缓存**：背景、路面标线、遮罩、文字、辉光文字、阴影、光晕全部缓存，
  每帧只做 blit。文字缓存用 LRU 淘汰，避免周期性重建造成的掉帧尖峰。
- **减少半透明混合面积**：路面标线做成"单条跑道一节"的窄条平铺，
  不再每次都遍历整行透明像素（0.23 ms → 0.03 ms）。
- **加载动画**：启动时分批加载资源，以 `loading_bg.png` 为背景，
  带进度条、当前步骤和跑动小人。
- **按钮化菜单**：开始 / 重开 / 退出都是可点击按钮，带呼吸光晕、
  悬停高亮和按下反馈，触摸与鼠标通用。
- **操作与规则提醒**：开始游戏前在开始界面统一展示键位与玩法说明，
  进入游戏后画面全部留给跑道（原来的右侧说明栏已移除）。

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
python tools/smoke_test.py        # 资源 + 逻辑 + 四界面渲染 + 按钮
python tools/test_screen_fit.py   # 各机型比例匹配 / 画布像素量 / 难度一致性
python tools/test_perf.py         # 绘制耗时基准
python tools/bench_render.py      # 凝视开销分解 + 各 RENDER_SCALE 的耗时对比
python tools/profile_frame.py     # 逐帧耗时分解（怀疑掉帧时先跑这个）
python tools/preview_ui.py        # 出界面截图，肉眼验收布局
```

前三个输出 `SMOKE OK` / `SCREEN FIT OK` / `PERF OK` 即正常。
调清晰度之前先跑 `bench_render.py`：它会给出每个 `RENDER_SCALE` 对应的
绘制耗时，照着 `test_perf.py` 的 3 ms 预算挑就行。

重新生成图标与加载背景（源图是 `kkphoto.png` / `beijing.png`）：

```
python tools/prep_assets.py
```
