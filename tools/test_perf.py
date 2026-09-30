# -*- coding: utf-8 -*-
"""渲染性能基准：在模拟手机分辨率下测每帧绘制耗时。

pygame 是软件渲染，画布越大越吃力。这个脚本用来确认"提升清晰度"之后
帧率是否还能站得住（目标：平均帧耗时 < 16.7ms，即 60 FPS）。
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import kunkun_da_tao_wang as g  # noqa: E402

DEVICES = [("主流 1080x2400", 1080, 2400), ("2K 1440x3200", 1440, 3200)]

g._screen_fit_enabled = lambda: True

worst = 0.0
for name, w, h in DEVICES:
    g._query_screen_size = lambda w=w, h=h: (w, h)
    t0 = time.perf_counter()
    game = g.Game()
    load_s = time.perf_counter() - t0

    game.reset_game()
    game.state = "playing"
    # 预热：让文字缓存、Surface 缓存都建立起来
    for _ in range(30):
        game.update(1 / 60)
        game.update_particles(1 / 60)
        game.draw()

    N = 240
    t0 = time.perf_counter()
    for i in range(N):
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
    el = time.perf_counter() - t0

    per_ms = el / N * 1000
    worst = max(worst, per_ms)
    print(f"{name:<16} 画布 {game.screen.get_size()[0]}x{game.screen.get_size()[1]}"
          f"  加载 {load_s:.2f}s  平均 {per_ms:.2f} ms/帧  ≈ {N / el:.0f} FPS")

print("-" * 64)
print(f"最差平均帧耗时 = {worst:.2f} ms")
ok = worst < 16.7
print("PERF OK（可维持 60 FPS）" if ok else f"PERF WARN（{worst:.1f}ms 超出 16.7ms 预算）")
sys.exit(0 if ok else 1)
