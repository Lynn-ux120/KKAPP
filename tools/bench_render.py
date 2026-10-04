# -*- coding: utf-8 -*-
"""渲染基准：把"凝视掉帧"和"清晰度"两个诉求换算成可比较的毫秒数。

用法：
    python tools/bench_render.py            # 扫描 RENDER_SCALE 1.0 / 1.15 / 1.25 / 1.4
    python tools/bench_render.py 1080 2400  # 指定一个屏幕尺寸并做详细分解

profile_frame.py 只统计了 draw() 里被包住的几个子步骤，剩下的"其他"
没有名字。这个脚本补上：
  1. 按子系统拆干净 draw()，特别是凝视态独有的开销；
  2. 单独计时 display.flip()，并按渲染倍率扫描，
     用于回答"提高清晰度要付多少帧率代价"。

所有测试都在 software 渲染后端下进行 —— 这是手机没有可用 GPU 渲染后端
时的最坏情况，也是我们唯一能可靠复现的基准。
"""
import os
import subprocess
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import pygame  # noqa: E402
import kunkun_da_tao_wang as g  # noqa: E402


def timeit(fn, n=200, warm=25, batches=5):
    """平均毫秒数，取多个批次的最小值。

    单批平均值的抖动能到 ±1 ms（占信号的 20%），足以把优化效果淹没。
    取"最快的一批"更接近真实能力，也让 A/B 对比可靠得多。
    """
    for _ in range(warm):
        fn()
    best = float("inf")
    for _ in range(batches):
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        best = min(best, (time.perf_counter() - t0) / n * 1000.0)
    return best


def make_game(screen_w, screen_h):
    g._screen_fit_enabled = lambda: True
    g._query_screen_size = lambda: (screen_w, screen_h)
    game = g.Game()
    game.reset_game()
    game.state = "playing"
    return game


# ----------------------------------------------------------------------
# 详细分解
# ----------------------------------------------------------------------
def detail(screen_w, screen_h):
    game = make_game(screen_w, screen_h)
    px_m = g.WIDTH * g.HEIGHT / 1e6
    print(f"屏幕 {screen_w}x{screen_h}   画布 {g.WIDTH}x{g.HEIGHT}   "
          f"({px_m:.2f}M 像素)   _S={g._S:.2f}")
    print("-" * 62)

    game.gaze = False
    for ch in game.chasers:
        ch.set_gaze(False)
    print(f"  {'背景 blit（常态）':<24}{timeit(game.draw_background):>7.2f} ms")
    game.gaze = True
    print(f"  {'背景 blit（凝视红版）':<24}{timeit(game.draw_background):>7.2f} ms")
    game.gaze = False

    print(f"  {'路面标线':<24}{timeit(game.draw_road_marks):>7.2f} ms")
    print(f"  {'HUD':<24}{timeit(game.draw_hud):>7.2f} ms")

    def draw_entities():
        for o in game.obstacles:
            o.draw(game.screen)
        for p in game.powerups:
            p.draw(game.screen, 0.5)
        for c in game.chasers:
            c.draw(game.screen)
        game.player.draw(game.screen)

    print(f"  {'全部实体':<24}{timeit(draw_entities):>7.2f} ms")

    game.gaze = False
    normal = timeit(game.draw)
    game.gaze = True
    for ch in game.chasers:
        ch.set_gaze(True)
    gazing = timeit(game.draw)
    game.gaze = False
    for ch in game.chasers:
        ch.set_gaze(False)
    flip = timeit(pygame.display.flip, n=120, warm=15)

    print("-" * 62)
    print(f"  {'draw() 常态':<24}{normal:>7.2f} ms  ≈ {1000 / normal:.0f} FPS")
    print(f"  {'draw() 凝视':<24}{gazing:>7.2f} ms  ≈ {1000 / gazing:.0f} FPS")
    print(f"  {'凝视额外开销':<24}{gazing - normal:>7.2f} ms")
    print(f"  {'（其中）display.flip':<24}{flip:>7.2f} ms")
    return px_m, normal, gazing


# ----------------------------------------------------------------------
# 倍率扫描：用子进程加载不同的 KK_RENDER_SCALE
# ----------------------------------------------------------------------
def sweep(screen_w, screen_h):
    print(f"扫描 RENDER_SCALE（屏幕 {screen_w}x{screen_h}，software 渲染）")
    print("-" * 74)
    print(f"{'倍率':<8}{'画布':<14}{'像素':<10}{'draw常态':<11}"
          f"{'draw凝视':<11}{'凝视增量':<10}")
    for s in ("1.0", "1.15", "1.25", "1.35", "1.5"):
        env = dict(os.environ, KK_RENDER_SCALE=s, KK_BENCH_ONE="1",
                   KK_BENCH_SCREEN=f"{screen_w}x{screen_h}")
        r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                           capture_output=True, env=env)
        line = r.stdout.decode("utf-8", "replace").strip().splitlines()
        if not line:
            print(f"{s:<8}(失败) {r.stderr.decode('utf-8', 'replace')[-200:]}")
            continue
        print(line[-1])
    print()
    print("注意：手机 CPU 通常比本机慢 3~6 倍，把上表数值乘以 3~6 估算真机；")
    print("      预算 16.7 ms/帧（60 FPS）。")


def one():
    """子进程模式：只打印一行汇总。"""
    sw, sh = os.environ["KK_BENCH_SCREEN"].split("x")
    game = make_game(int(sw), int(sh))
    game.gaze = False
    n = timeit(game.draw, n=120, warm=20)
    game.gaze = True
    for ch in game.chasers:
        ch.set_gaze(True)
    z = timeit(game.draw, n=120, warm=20)
    print(f"{g._S:<8}{g.WIDTH}x{g.HEIGHT:<9}"
          f"{g.WIDTH * g.HEIGHT / 1e6:<10.2f}{n:<11.2f}{z:<11.2f}{z - n:<10.2f}")


def main():
    if os.environ.get("KK_BENCH_ONE"):
        one()
        return
    if len(sys.argv) >= 3:
        detail(int(sys.argv[1]), int(sys.argv[2]))
    else:
        px_m, n, z = detail(1080, 2400)
        print()
        sweep(1080, 2400)
    print()
    print("BENCH DONE")


if __name__ == "__main__":
    main()
