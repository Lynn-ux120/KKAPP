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
tools/gen_icon.py                ← 重新生成图标
```

## 操作方式

| 按键 | 作用 |
| --- | --- |
| 左 / 右方向键 或 A / D | 在 3 条跑道间切换（切换会重置凝视倒计时） |
| 上方向键 / W / 空格 | 跳跃（可跳过矮障碍：黑板擦、试卷） |
| ESC | 退出游戏 |
| R（游戏结束后） | 重新开始 |

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

改完代码先跑一遍冒烟测试，能提前发现资源缺失或渲染错误：

```
python tools/smoke_test.py
```

输出 `SMOKE OK` 即正常。
