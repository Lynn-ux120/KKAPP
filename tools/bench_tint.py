# -*- coding: utf-8 -*-
"""凝视红罩的几种实现方式成本对比。

现状是全画布 SRCALPHA blit（每像素 alpha 混合），是凝视态最贵的一步。
这里对比几种等效/近似的替代方案，挑选最便宜的。
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
W, H = 720, 1600
screen = pygame.display.set_mode((W, H))
screen.fill((40, 50, 90))

# 方案 A：现状 —— 全画布 SRCALPHA blit
overlay = pygame.Surface((W, H), pygame.SRCALPHA)
overlay.fill((255, 0, 0, 26))

# 方案 B：整屏 fill + BLEND_RGB_ADD（无 alpha 混合，纯加法）
# 方案 C：上/下/左/右四条渐变边（暗角），只覆盖边缘区域
vig_h = 260
top = pygame.Surface((W, vig_h), pygame.SRCALPHA)
for y in range(vig_h):
    top.fill((150, 0, 0, int(70 * (1 - y / vig_h) ** 1.6)), (0, y, W, 1))
bot = pygame.transform.flip(top, False, True)

# 方案 D：预先把红调进背景（背景是静态的，直接多缓存一张红版）
bg = pygame.Surface((W, H))
bg.fill((40, 50, 90))
bg_red = bg.copy()
bg_red.fill((26, 0, 0), special_flags=pygame.BLEND_RGB_ADD)


def timeit(fn, n=200, warm=30):
    for _ in range(warm):
        fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n * 1000.0


opts = [
    ("A 全屏 SRCALPHA blit（现状）", lambda: screen.blit(overlay, (0, 0))),
    ("B fill + BLEND_RGB_ADD", lambda: screen.fill((26, 0, 0),
                                                   special_flags=pygame.BLEND_RGB_ADD)),
    ("C 暗角双条 blit", lambda: (screen.blit(top, (0, 0)),
                                 screen.blit(bot, (0, H - vig_h)))),
    ("D 换成红版背景 blit", lambda: screen.blit(bg_red, (0, 0))),
    ("   对照：普通背景 blit", lambda: screen.blit(bg, (0, 0))),
]

print(f"画布 {W}x{H}  ({W * H / 1e6:.2f}M 像素)")
print("-" * 52)
for name, fn in opts:
    print(f"  {name:<28}{timeit(fn):>7.2f} ms")
print()
print("TINT BENCH DONE")
