# -*- coding: utf-8 -*-
"""屏幕适配验证：模拟常见手机分辨率。

关注四个指标：
  1. 比例偏差 —— 画布宽高比与屏幕宽高比的相对误差。越接近 0，SCALED 缩放后
                越不会有黑边、也不会被拉伸变形（overscan 模式下靠这个保证无形变）
  2. 画布像素 —— 决定 CPU 软件渲染的负担，越小越流畅（这是掉帧的直接变量）
  3. 判定线距底 —— 玩家距画布底部的距离，应保持恒定，角色才会贴在屏幕下方
  4. 预警秒   —— 障碍从顶端落到判定线的时间，应保持恒定，难度手感才一致
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import kunkun_da_tao_wang as g  # noqa: E402

# 最后一组 (0, 0) 表示屏幕尺寸探测失败，应退回设计稿比例
DEVICES = [
    ("主流 1080x2400", 1080, 2400),
    ("iPhone 1170x2532", 1170, 2532),
    ("21:9 1080x2520", 1080, 2520),
    ("老机型 720x1280", 720, 1280),
    ("2K 1440x3200", 1440, 3200),
    ("超长 1080x2800", 1080, 2800),
    ("平板竖屏 2048x2732", 2048, 2732),
    # 部分安卓设备会把屏幕报告成横屏，应被归一带入同一结果
    ("横屏报告 2400x1080", 2400, 1080),
]

REF_PREVIEW = (640 + 130) / 240.0        # 设计稿下障碍落到判定线所需秒数
PIXEL_BUDGET = 1_400_000                 # 单帧画布像素预算

print(f"{'设备':<20}{'逻辑画布':>11}{'比例偏差':>9}{'像素':>10}"
      f"{'距底':>6}{'预警秒':>8}")
print("-" * 68)

# 桌面默认不启用自适应，这里强制开启以模拟真机
g._screen_fit_enabled = lambda: True

worst_ratio_err = 0.0
worst_pixels = 0
previews = []
ok = True

for name, w, h in DEVICES:
    g._query_screen_size = lambda w=w, h=h: (w, h)
    game = g.Game()
    lw, lh = game.screen.get_size()

    # 与游戏内部一致：短边为宽、长边为高
    sw, sh = (w, h) if w <= h else (h, w)
    ratio_err = abs((lw / lh) - (sw / sh)) / (sw / sh)
    pixels = lw * lh

    bottom_gap = g.HEIGHT - g.PLAYER_Y
    desk_h = g.px(g.Obstacle.SPEC["desk"]["h"])
    preview = (g.PLAYER_Y + desk_h) / g.OBSTACLE_SPEED_BASE

    worst_ratio_err = max(worst_ratio_err, ratio_err)
    worst_pixels = max(worst_pixels, pixels)
    previews.append(preview)

    print(f"{name:<20}{f'{lw}x{lh}':>11}{ratio_err:>9.2%}"
          f"{f'{pixels / 1e6:.2f}M':>10}{bottom_gap:>6}{preview:>8.2f}")

print("-" * 68)

if worst_ratio_err > 0.12:
    print(f"[FAIL] 最大比例偏差 {worst_ratio_err:.1%}，画面会被明显拉伸或留黑边")
    ok = False
elif worst_ratio_err > 0.02:
    print(f"[WARN] 最大比例偏差 {worst_ratio_err:.1%}（画布高度被上下限夹取所致）")
else:
    print(f"最大比例偏差 = {worst_ratio_err:.2%}（画布与屏幕同比例，零黑边无形变）")

if worst_pixels > PIXEL_BUDGET:
    print(f"[FAIL] 单帧画布像素达 {worst_pixels / 1e6:.2f}M，超出预算 "
          f"{PIXEL_BUDGET / 1e6:.1f}M，手机上会掉帧")
    ok = False
else:
    print(f"单帧画布像素 {worst_pixels / 1e6:.2f}M ≤ 预算 {PIXEL_BUDGET / 1e6:.1f}M")

drift = max(abs(p - REF_PREVIEW) / REF_PREVIEW for p in previews)
if drift > 0.08:
    print(f"[FAIL] 预警时间相对设计稿漂移 {drift:.1%}，难度手感不一致")
    ok = False
else:
    print(f"难度漂移 = {drift:.1%}（<8%，各机型手感一致）")

# ---- 探测失败时的兜底 ----
g._query_screen_size = lambda: (0, 0)
fallback = g.Game()
fw, fh = fallback.screen.get_size()
print(f"探测失败兜底 -> 画布 {fw}x{fh}，缩放模式 = "
      f"{os.environ.get('SDL_RENDER_LOGICAL_SIZE_MODE')}")
if (fw, fh) != (g.DESIGN_W, g.DESIGN_H):
    print("[FAIL] 探测失败时应退回设计稿尺寸")
    ok = False
if os.environ.get("SDL_RENDER_LOGICAL_SIZE_MODE") != "letterbox":
    print("[FAIL] 探测失败时应改用 letterbox，避免把设计稿比例硬拉伸")
    ok = False

print("SCREEN FIT OK" if ok else "SCREEN FIT FAILED")
sys.exit(0 if ok else 1)
