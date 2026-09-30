# -*- coding: utf-8 -*-
"""素材预处理：抹掉原图右下角的「千问」水印，并生成应用图标与加载背景。

输入（工程根目录）：
    kkphoto.png    1024x1024  角色立绘，作为应用图标来源
    beijing.png    720x1280   地铁隧道场景，作为启动加载界面背景

输出：
    icon.png        512x512   应用图标
    loading_bg.png  720x1280  加载界面背景（已去水印）

去水印用的是拉普拉斯平滑：以水印矩形四周的像素为边界条件，向内部迭代
扩散出平滑渐变。背景本身是平滑的渐变/铁轨纹理，所以补完看不出痕迹。

用法：
    python tools/prep_assets.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import pygame  # noqa: E402

# 水印矩形 (x0, y0, x1, y1)，含少量余量避免留下半透明残影
ICON_WM = (866, 912, 1012, 994)      # kkphoto.png 右下角
BG_WM = (600, 1208, 714, 1276)       # beijing.png 右下角

ICON_SIZE = 512


def inpaint(surf, rect, iters=24):
    """用水印矩形边界的颜色向内部平滑扩散，覆盖掉水印。"""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    top = [surf.get_at((x0 + x, y0 - 1))[:3] for x in range(w)]
    bot = [surf.get_at((x0 + x, y1))[:3] for x in range(w)]
    lef = [surf.get_at((x0 - 1, y0 + y))[:3] for y in range(h)]
    rig = [surf.get_at((x1, y0 + y))[:3] for y in range(h)]

    # 初值：上下与左右两组边界值的双线性混合
    grid = []
    for y in range(h):
        fy = (y + 0.5) / h
        row = []
        for x in range(w):
            fx = (x + 0.5) / w
            vert = [top[x][i] * (1 - fy) + bot[x][i] * fy for i in range(3)]
            horz = [lef[y][i] * (1 - fx) + rig[y][i] * fx for i in range(3)]
            row.append([vert[i] * (1 - fx) + horz[i] * fx for i in range(3)])
        grid.append(row)

    # 迭代平滑（四邻平均），边界固定
    for _ in range(iters):
        new = []
        for y in range(h):
            row = []
            for x in range(w):
                acc = [0.0, 0.0, 0.0]
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w:
                        c = grid[ny][nx]
                    elif ny < 0:
                        c = top[x]
                    elif ny >= h:
                        c = bot[x]
                    elif nx < 0:
                        c = lef[y]
                    else:
                        c = rig[y]
                    acc[0] += c[0]
                    acc[1] += c[1]
                    acc[2] += c[2]
                row.append([acc[0] / 4.0, acc[1] / 4.0, acc[2] / 4.0])
            new.append(row)
        grid = new

    for y in range(h):
        for x in range(w):
            c = grid[y][x]
            surf.set_at((x0 + x, y0 + y),
                        (int(c[0] + 0.5), int(c[1] + 0.5), int(c[2] + 0.5)))


def main():
    pygame.init()
    pygame.display.set_mode((64, 64))

    icon_src = os.path.join(BASE, "kkphoto.png")
    icon_raw = pygame.image.load(icon_src).convert()
    inpaint(icon_raw, ICON_WM)
    icon = pygame.transform.smoothscale(icon_raw, (ICON_SIZE, ICON_SIZE)).convert()
    pygame.image.save(icon, os.path.join(BASE, "icon.png"))
    print(f"icon.png       {ICON_SIZE}x{ICON_SIZE}")

    bg_src = os.path.join(BASE, "beijing.png")
    bg = pygame.image.load(bg_src).convert()
    inpaint(bg, BG_WM)
    pygame.image.save(bg, os.path.join(BASE, "loading_bg.png"))
    print(f"loading_bg.png {bg.get_width()}x{bg.get_height()}")

    pygame.quit()


if __name__ == "__main__":
    main()
