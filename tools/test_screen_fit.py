# -*- coding: utf-8 -*-
"""屏幕自适应验证：模拟常见手机分辨率，确认逻辑画布能铺满屏幕且难度手感不变。

关注三个指标：
  1. 黑边 —— 缩放后画布与屏幕的差值，应接近 0（越小越铺满）
  2. 判定线 —— 玩家距画布底部的距离，应保持恒定（角色始终在屏幕下方）
  3. 预警秒 —— 障碍从顶部落到判定线的时间，应保持恒定（难度不变）
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import kunkun_da_tao_wang as g  # noqa: E402

DEVICES = [
    ("主流 1080x2400", 1080, 2400),
    ("iPhone 1170x2532", 1170, 2532),
    ("21:9 1080x2520", 1080, 2520),
    ("老机型 720x1280", 720, 1280),
    ("2K 1440x3200", 1440, 3200),
    ("平板竖屏 2048x2732", 2048, 2732),
    # 部分安卓设备会把屏幕报告成横屏，应被归一带入同一结果
    ("横屏报告 2400x1080", 2400, 1080),
]

# 对照基准：设计稿 720x820 时的表现
REF_PREVIEW = (640 + 130) / 240.0

print(f"{'设备':<18}{'逻辑画布':>11}{'缩放':>6}{'黑边':>8}"
      f"{'判定线':>7}{'距底':>6}{'预警秒':>8}")
print("-" * 68)

worst_gap = 0
previews = []
# 桌面默认不启用自适应，这里强制开启以模拟真机
g._screen_fit_enabled = lambda: True

for name, w, h in DEVICES:
    g._query_screen_size = lambda w=w, h=h: (w, h)
    game = g.Game()
    lw, lh = game.screen.get_size()

    # 与游戏内部一致：短边为宽、长边为高
    sw, sh = (w, h) if w <= h else (h, w)
    scale = min(sw / lw, sh / lh)        # SCALED 等比缩放：取较小的一边
    dw, dh = lw * scale, lh * scale
    gap = max(sw - dw, sh - dh)          # 单边最大黑边像素

    bottom_gap = g.HEIGHT - g.PLAYER_Y   # 判定线距画布底部
    preview = (g.PLAYER_Y + 130) / g.OBSTACLE_SPEED_BASE  # 桌子(h=130)的预警时间

    worst_gap = max(worst_gap, gap)
    previews.append(preview)
    print(f"{name:<18}{f'{lw}x{lh}':>11}{scale:>6.2f}{f'{int(gap)}px':>8}"
          f"{g.PLAYER_Y:>7}{bottom_gap:>6}{preview:>8.2f}")

print("-" * 68)
print(f"设计稿基准预警秒 = {REF_PREVIEW:.2f}")
print(f"最大黑边 = {int(worst_gap)}px")

ok = True
if worst_gap > 8:
    print("[FAIL] 存在明显黑边，画面没铺满")
    ok = False
# 障碍高度(130)与底部留白(180)是固定像素、不随画布缩放，
# 因此各机型的预警时间天然有几个百分点的差异，8% 以内视为手感一致。
drift = max(abs(p - REF_PREVIEW) / REF_PREVIEW for p in previews)
if drift > 0.08:
    print(f"[FAIL] 预警时间相对基准漂移 {drift:.1%}，难度手感不一致")
    ok = False
else:
    print(f"难度漂移 = {drift:.1%}（<8%，各机型手感一致）")

print("SCREEN FIT OK" if ok else "SCREEN FIT FAILED")
sys.exit(0 if ok else 1)
