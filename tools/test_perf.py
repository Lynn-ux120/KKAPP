# -*- coding: utf-8 -*-
"""渲染性能基准：在模拟手机分辨率下测每帧耗时。

pygame 是软件渲染，画布越大越吃力。这里刻意把两件事分开量：

  * 绘制耗时 —— 我们自己画的像素（背景、标线、人物、HUD）。这部分是
    代码能优化的对象，也是这个脚本的 PASS/FAIL 依据。
  * flip 耗时 —— 把画布缩放送到屏幕。量级由输出分辨率决定，本机（software
    后端 + dummy 全屏）的数值和真机没有可比性，只作为参考打印出来。

真机上的真实耗时 = 绘制 × (手机 CPU/本机 CPU) + flip（若走 GPU 则极低）。
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import pygame  # noqa: E402
import kunkun_da_tao_wang as g  # noqa: E402

DEVICES = [("主流 1080x2400", 1080, 2400), ("2K 1440x3200", 1440, 3200)]

# 绘制部分的预算。留出充分余量：真机 CPU 通常慢 3~6 倍，
# 绘制压在 3 ms 以内，乘 6 仍不到 19 ms，配合 GPU 版 flip 才有 60 FPS 的余裕。
DRAW_BUDGET_MS = 3.0

g._screen_fit_enabled = lambda: True

real_flip = pygame.display.flip
worst_draw = 0.0
ok = True

print(f"RENDER_SCALE = {g.RENDER_SCALE}   （画布宽 = {g.DESIGN_W}）")
print("-" * 72)

for name, w, h in DEVICES:
    g._query_screen_size = lambda w=w, h=h: (w, h)
    t0 = time.perf_counter()
    game = g.Game()
    load_s = time.perf_counter() - t0

    game.reset_game()
    game.state = "playing"
    lw, lh = game.screen.get_size()

    def step(i):
        if i % 30 == 5:
            game.player.move(-1)
        if i % 30 == 15:
            game.player.move(1)
        if i % 45 == 20:
            game.player.jump()
        game.handle_events()
        game.update(1 / 60)
        game.update_particles(1 / 60)
        game.draw()

    for i in range(40):                       # 预热，建立各种缓存
        step(i)

    # ---- 只算绘制：把 flip 换成空操作 ----
    pygame.display.flip = lambda: None
    N = 300
    t0 = time.perf_counter()
    for i in range(N):
        step(i)
    draw_ms = (time.perf_counter() - t0) / N * 1000
    pygame.display.flip = real_flip

    # ---- flip 单独量 ----
    t0 = time.perf_counter()
    for _ in range(120):
        real_flip()
    flip_ms = (time.perf_counter() - t0) / 120 * 1000

    worst_draw = max(worst_draw, draw_ms)
    if draw_ms > DRAW_BUDGET_MS:
        ok = False
    print(f"{name:<16} 画布 {lw}x{lh}  {lw * lh / 1e6:.2f}M 像素  "
          f"加载 {load_s:.2f}s")
    print(f"{'':<16} 绘制 {draw_ms:.2f} ms  |  flip {flip_ms:.2f} ms（参考）"
          f"  |  合计 {draw_ms + flip_ms:.2f} ms")

print("-" * 72)
print(f"最差绘制耗时 = {worst_draw:.2f} ms（预算 {DRAW_BUDGET_MS:.1f} ms）")
print("PERF OK（绘制部分留有余量）" if ok
      else f"PERF WARN（绘制 {worst_draw:.1f}ms 超出预算，建议调小 RENDER_SCALE）")
sys.exit(0 if ok else 1)
