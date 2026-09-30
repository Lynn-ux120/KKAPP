# -*- coding: utf-8 -*-
"""逐帧耗时分解：定位渲染管线里最吃时间的一环。

掉帧来自"每帧要写入的像素总量"以及 Python 层的调用开销，
这个脚本把 draw() 拆开分别计时，避免凭感觉优化。
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import kunkun_da_tao_wang as g  # noqa: E402

SCREEN = (1080, 2400)
g._screen_fit_enabled = lambda: True
g._query_screen_size = lambda: SCREEN

game = g.Game()
game.reset_game()
game.state = "playing"

TARGETS = ["draw_background", "draw_road_marks", "draw_hud", "update",
           "update_particles", "draw"]
timers = {name: 0.0 for name in TARGETS}
calls = {name: 0 for name in TARGETS}

# 把 draw 里的各子步骤单独计时（draw 本身也计时，用于算"其他"）
for name in TARGETS:
    orig = getattr(game, name)

    def make(orig=orig, name=name):
        def timed(*a, **k):
            t0 = time.perf_counter()
            r = orig(*a, **k)
            timers[name] += time.perf_counter() - t0
            calls[name] += 1
            return r
        return timed

    setattr(game, name, make())

# 单独给每个实体绘制计时
ent_times = {}
for cls in (g.Obstacle, g.PowerUp, g.Player, g.Chaser):
    orig = cls.draw
    key = cls.__name__

    def make2(orig=orig, key=key):
        def timed(self, *a, **k):
            t0 = time.perf_counter()
            r = orig(self, *a, **k)
            ent_times[key] = ent_times.get(key, 0.0) + (time.perf_counter() - t0)
            return r
        return timed

    cls.draw = make2()

# 粒子单独计时
orig_particle_draw = g.Particle.draw


def particle_draw(self, screen):
    t0 = time.perf_counter()
    r = orig_particle_draw(self, screen)
    ent_times["Particle"] = ent_times.get("Particle", 0.0) + (time.perf_counter() - t0)
    return r


g.Particle.draw = particle_draw

N = 300
for _ in range(30):                     # 预热
    game.update(1 / 60)
    game.update_particles(1 / 60)
    game.draw()

for k in timers:
    timers[k] = 0.0
    calls[k] = 0
for k in ent_times:
    ent_times[k] = 0.0

t_all = time.perf_counter()
for _ in range(N):
    game.handle_events()
    game.update(1 / 60)
    game.update_particles(1 / 60)
    game.draw()
total = time.perf_counter() - t_all

per = total / N * 1000
print(f"画布 = {game.screen.get_size()}  ({g.WIDTH * g.HEIGHT / 1e6:.2f}M 像素)")
print(f"总平均 = {per:.2f} ms/帧  ≈ {1000 / per:.0f} FPS")
print("-" * 56)
for name in TARGETS:
    print(f"  {name:<20}{timers[name] / N * 1000:>7.2f} ms/帧"
          f"   调用 {calls[name] // N}/帧")
print("-" * 56)
for k, v in sorted(ent_times.items(), key=lambda kv: -kv[1]):
    if v > 0:
        print(f"  {k:<20}{v / N * 1000:>7.2f} ms/帧")

sub = timers["draw_background"] + timers["draw_road_marks"] + timers["draw_hud"]
other = timers["draw"] - sub
print("-" * 56)
print(f"  {'背景+标线+HUD 之外':<20}{other / N * 1000:>7.2f} ms/帧")

pygame_flip = timers["draw"]
print(f"{'':<22}其中 draw() 整体占比 = {pygame_flip / total:.0%}")
