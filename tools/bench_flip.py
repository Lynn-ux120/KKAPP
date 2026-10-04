# -*- coding: utf-8 -*-
"""量化 display.flip() 的成本：缩放质量与画布尺寸各占多少。

结论直接影响两个决策：
  - 清晰度能往上提多少（画布越大越清晰，但可能越慢）
  - 是否值得把 SDL 的缩放滤波从线性换成最近邻
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import pygame  # noqa: E402


def bench(canvas, out_size, quality, n=150, warm=25):
    """在给定画布尺寸/输出尺寸/缩放质量下，测 flip 平均毫秒。"""
    pygame.display.quit()
    pygame.display.init()
    os.environ["SDL_RENDER_SCALE_QUALITY"] = str(quality)
    pygame.display.set_mode(canvas, pygame.SCALED)
    surf = pygame.display.get_surface()
    # 填点东西，避免全是同一色导致的缓存假象
    for y in range(0, canvas[1], 37):
        pygame.draw.line(surf, (y % 255, 60, 120), (0, y), (canvas[0], y))
    for _ in range(warm):
        pygame.display.flip()
    t0 = time.perf_counter()
    for _ in range(n):
        pygame.display.flip()
    return (time.perf_counter() - t0) / n * 1000.0


def bench_noscale(canvas, n=150, warm=25):
    """不带 SCALED，直接 set_mode：flip 只做一次纯拷贝。"""
    pygame.display.quit()
    pygame.display.init()
    pygame.display.set_mode(canvas)
    surf = pygame.display.get_surface()
    for y in range(0, canvas[1], 37):
        pygame.draw.line(surf, (y % 255, 60, 120), (0, y), (canvas[0], y))
    for _ in range(warm):
        pygame.display.flip()
    t0 = time.perf_counter()
    for _ in range(n):
        pygame.display.flip()
    return (time.perf_counter() - t0) / n * 1000.0


def main():
    print("=" * 74)
    print("flip() 成本：缩放质量 x 画布尺寸   (software 渲染器 = 最坏情况)")
    print("=" * 74)
    print(f"{'画布':<12}{'像素':<10}{'quality=0':<12}{'quality=1':<12}"
          f"{'无SCALED':<12}")
    for w, h in [(720, 1280), (720, 1600), (720, 1800),
                 (900, 2000), (1080, 2400)]:
        px = w * h / 1e6
        a = bench((w, h), None, 0)
        b = bench((w, h), None, 1)
        c = bench_noscale((w, h))
        print(f"{w}x{h:<7}{px:<10.2f}{a:<12.2f}{b:<12.2f}{c:<12.2f}")

    print()
    print("=" * 74)
    print("固定画布 720x1600，改变输出：看 flip 是否随输出像素增长")
    print("=" * 74)
    pygame.display.quit()
    print("（dummy 驱动下窗口即输出，此处仅作对照）")
    print("BENCH2 DONE")


if __name__ == "__main__":
    main()
